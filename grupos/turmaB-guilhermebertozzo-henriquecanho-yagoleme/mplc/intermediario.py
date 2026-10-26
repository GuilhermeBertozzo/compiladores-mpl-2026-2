"""AST anotada -> IR de tres enderecos, independente da arvore e da VM.

Bindings semanticos recebem nomes vN, separados dos temporarios tN.
Conversoes sao instrucoes explicitas no ponto de consumo, nunca mudam
o tipo de uma operacao ja traduzida.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import json


@dataclass(frozen=True)
class Instrucao:
    op: str
    destino: object = None
    args: tuple = ()
    linha: int = 1
    coluna: int = 1


@dataclass
class Funcao:
    nome: str
    tipo: str
    parametros: list
    instrucoes: list = field(default_factory=list)


@dataclass
class Codigo:
    funcoes: list = field(default_factory=list)


class _Tradutor:
    def __init__(self):
        self.codigo = Codigo()
        self.bindings = {}
        self.temporarios = 0
        self.rotulos = 0
        self.funcao = None

    def slot(self, no):
        binding = no.extra['slot']
        if binding not in self.bindings:
            self.bindings[binding] = f'v{len(self.bindings)}'
        return self.bindings[binding]

    def temporario(self):
        nome = f't{self.temporarios}'
        self.temporarios += 1
        return nome

    def rotulo(self):
        nome = f'L{self.rotulos}'
        self.rotulos += 1
        return nome

    def emitir(self, op, pos, destino=None, *args):
        self.funcao.instrucoes.append(Instrucao(op, destino, args, *pos))

    def valor(self, op, pos, *args):
        destino = self.temporario()
        self.emitir(op, pos, destino, *args)
        return destino

    def converter(self, valor, origem, destino, pos):
        if origem == 'inteiro' and destino == 'real':
            return self.valor('i2r', pos, valor)
        return valor

    def consumir(self, no, tipo, pos):
        valor = self.expressao(no, pos)
        return self.converter(valor, no.extra['tipo'], tipo, pos)

    def expressao(self, no, pos):
        kind = no.extra['kind']
        if kind == 'literal':
            return self.valor('const', pos, no.extra['valor'])
        if kind == 'variavel':
            return self.valor('copy', pos, self.slot(no))
        if kind == 'unario':
            valor = self.expressao(no.filhos[0], pos)
            return self.valor('unary', pos, no.extra['op'], valor,
                              no.filhos[0].extra['tipo'])
        if kind == 'binario':
            esquerda, direita = no.filhos
            te, td = esquerda.extra['tipo'], direita.extra['tipo']
            # Comparacoes tem resultado logico, mas operandos numericos
            # mistos ainda exigem promocao para real.
            tipo = 'real' if {te, td} == {'inteiro', 'real'} else te
            a = self.consumir(esquerda, tipo, pos)
            b = self.consumir(direita, tipo, pos)
            return self.valor('binary', pos, no.extra['op'], a, b, tipo)
        if kind == 'chamada':
            argumentos = tuple(self.consumir(arg, tipo, pos)
                               for arg, tipo in zip(no.filhos, no.extra['param_tipos']))
            for argumento in argumentos:
                self.emitir('param', pos, None, argumento)
            destino = None if no.extra['tipo'] == 'vazio' else self.temporario()
            self.emitir('call', pos, destino, no.extra['nome'], len(argumentos))
            return destino
        raise ValueError(f'expressao desconhecida na IR: {kind}')

    def comando(self, no):
        kind = no.extra['kind']
        pos = (no.linha, no.coluna)
        if kind == 'bloco':
            for filho in no.filhos:
                self.comando(filho)
        elif kind in ('declaracao', 'atribuicao'):
            if no.filhos:
                valor = self.consumir(no.filhos[0], no.extra['tipo'], pos)
            else:
                padrao = {'inteiro': 0, 'real': 0.0, 'logico': False, 'texto': ''}
                valor = self.valor('const', pos, padrao[no.extra['tipo']])
            self.emitir('copy', pos, self.slot(no), valor)
        elif kind == 'escreva':
            valor = self.expressao(no.filhos[0], pos)
            self.emitir('write', pos, None, valor, no.filhos[0].extra['tipo'])
        elif kind == 'retorne':
            args = ()
            if no.filhos:
                args = (self.consumir(no.filhos[0], no.extra['destino_tipo'], pos),)
            self.emitir('return', pos, None, *args)
        elif kind == 'chamada':
            self.expressao(no, pos)
        elif kind == 'se':
            senao, fim = self.rotulo(), self.rotulo()
            condicao = self.expressao(no.filhos[0], pos)
            self.emitir('jfalse', pos, None, condicao, senao)
            self.comando(no.filhos[1])
            self.emitir('jump', pos, None, fim)
            self.emitir('label', pos, None, senao)
            if len(no.filhos) == 3:
                self.comando(no.filhos[2])
            self.emitir('label', pos, None, fim)
        elif kind == 'enquanto':
            inicio, fim = self.rotulo(), self.rotulo()
            self.emitir('label', pos, None, inicio)
            condicao = self.expressao(no.filhos[0], pos)
            self.emitir('jfalse', pos, None, condicao, fim)
            self.comando(no.filhos[1])
            self.emitir('jump', pos, None, inicio)
            self.emitir('label', pos, None, fim)
        else:
            raise ValueError(f'comando desconhecido na IR: {kind}')

    def traduzir(self, arvore):
        for no in arvore.filhos:
            parametros, bloco = no.filhos
            self.funcao = Funcao(no.extra['nome'], no.extra['tipo'],
                                 [(self.slot(p), p.extra['tipo']) for p in parametros.filhos])
            self.codigo.funcoes.append(self.funcao)
            self.comando(bloco)
            pos = (no.linha, no.coluna)
            if self.funcao.tipo == 'vazio':
                self.emitir('return', pos)
            else:
                # A semantica garante retorno; protege tambem IR alterada.
                self.emitir('trap', pos, None, 'funcao terminou sem retorno')
        return self.codigo


def gerar(arvore, tabela):
    """Recebe No anotado pela semantica; nao retem AST nem tabela no IR."""
    return _Tradutor().traduzir(arvore)


def despejar(codigo):
    """Texto de tres enderecos: cada calculo tem no maximo um operador."""
    linhas = []
    for funcao in codigo.funcoes:
        params = ', '.join(f'{nome} {tipo}' for nome, tipo in funcao.parametros)
        linhas.append(f'funcao {funcao.nome} {funcao.tipo} ({params})')
        for i in funcao.instrucoes:
            a = i.args
            if i.op == 'const':
                valor = a[0]
                if type(valor) is bool:
                    literal = 'verdadeiro' if valor else 'falso'
                elif type(valor) is float:
                    # Expoentes como 1e-20 confundem a contagem de operadores
                    # do verificador ("e" logico e "-"). Usa forma decimal.
                    literal = format(Decimal(str(valor)), 'f')
                else:
                    literal = json.dumps(valor, ensure_ascii=True)
                texto = f'{i.destino} = {literal}'
            elif i.op == 'copy':
                texto = f'{i.destino} = {a[0]}'
            elif i.op == 'i2r':
                texto = f'{i.destino} = inteiroParaReal {a[0]}'
            elif i.op == 'binary':
                texto = f'{i.destino} = {a[1]} {a[0]} {a[2]}'
            elif i.op == 'unary':
                texto = f'{i.destino} = {a[0]} {a[1]}'
            elif i.op == 'param':
                texto = f'parametro {a[0]}'
            elif i.op == 'call':
                prefixo = f'{i.destino} = ' if i.destino else ''
                texto = f'{prefixo}chama {a[0]} {a[1]}'
            elif i.op == 'write':
                texto = f'escreva {a[0]}'
            elif i.op == 'return':
                texto = 'retorne' + (f' {a[0]}' if a else '')
            elif i.op == 'jump':
                texto = f'desvie {a[0]}'
            elif i.op == 'jfalse':
                texto = f'seFalso {a[0]} desvie {a[1]}'
            elif i.op == 'label':
                linhas.append(f'{a[0]}:')
                continue
            elif i.op == 'trap':
                texto = 'erro ' + json.dumps(a[0], ensure_ascii=False)
            else:
                raise ValueError(f'instrucao IR desconhecida: {i.op}')
            linhas.append('  ' + texto)
        linhas.append('fim')
    return linhas
