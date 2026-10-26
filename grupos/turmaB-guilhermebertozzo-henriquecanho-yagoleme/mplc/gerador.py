"""Traduz exclusivamente IR para bytecode textual MPLB 1.

Diretivas FUNC [nome, retorno, slots_parametros] e END delimitam funcoes.
Cada instrucao tem formato `linha:coluna OPCODE [argumentos JSON]`.
JSON preserva textos e escapes; nenhuma instrucao contem fonte ou AST.
"""
import json


def gerar(codigo_intermediario):
    """Devolve as linhas UTF-8 do .mplb, executavel sem acesso ao fonte."""
    linhas = ['MPLB 1']

    def emitir(op, args, instrucao):
        # Escapa tambem separadores Unicode, mantendo uma instrucao por linha.
        dados = json.dumps(args, ensure_ascii=True)
        linhas.append(f'{instrucao.linha}:{instrucao.coluna} {op} {dados}')

    for funcao in codigo_intermediario.funcoes:
        dados = [funcao.nome, funcao.tipo, [p[0] for p in funcao.parametros]]
        linhas.append('FUNC ' + json.dumps(dados, ensure_ascii=False))
        for i in funcao.instrucoes:
            a = i.args
            if i.op == 'const':
                emitir('PUSH', [a[0]], i)
            elif i.op in ('copy', 'i2r'):
                emitir('LOAD', [a[0]], i)
                if i.op == 'i2r':
                    emitir('I2R', [], i)
            elif i.op == 'binary':
                emitir('LOAD', [a[1]], i)
                emitir('LOAD', [a[2]], i)
                emitir('BINARY', [a[0], a[3]], i)
            elif i.op == 'unary':
                emitir('LOAD', [a[1]], i)
                emitir('UNARY', [a[0], a[2]], i)
            elif i.op == 'param':
                emitir('LOAD', [a[0]], i)
            elif i.op == 'call':
                emitir('CALL', [a[0], a[1]], i)
            elif i.op == 'write':
                emitir('LOAD', [a[0]], i)
                emitir('WRITE', [a[1]], i)
            elif i.op == 'return':
                if a:
                    emitir('LOAD', [a[0]], i)
                emitir('RETURN', [bool(a)], i)
            elif i.op == 'jfalse':
                emitir('LOAD', [a[0]], i)
                emitir('JUMP_FALSE', [a[1]], i)
            elif i.op in ('jump', 'label', 'trap'):
                emitir({'jump': 'JUMP', 'label': 'LABEL', 'trap': 'TRAP'}[i.op], list(a), i)
            else:
                raise ValueError(f'instrucao IR desconhecida: {i.op}')
            if i.destino is not None:
                emitir('STORE', [i.destino], i)
        linhas.append('END')
    return linhas
