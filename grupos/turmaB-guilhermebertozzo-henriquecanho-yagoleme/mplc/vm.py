"""VM iterativa para MPLB 1; nao importa parser, AST ou gerador.

Instrucoes e efeitos sobre a pilha (topo a direita):
  PUSH [valor]          S -> S, valor
  LOAD [slot]           S -> S, locais[slot]
  STORE [slot]          S, valor -> S; grava nos locais da ativacao atual
  I2R []                S, inteiro -> S, real
  BINARY [op, tipo]     S, esquerda, direita -> S, resultado
  UNARY [op, tipo]      S, operando -> S, resultado
  LABEL [rotulo]        S -> S; marca um destino de salto
  JUMP [rotulo]         S -> S; altera o contador de programa
  JUMP_FALSE [rotulo]   S, condicao -> S; salta quando falso
  CALL [nome, n]        S, arg0, ..., argN -> S; cria registro de ativacao
  RETURN [tem_valor]    devolve zero/um valor ao chamador e remove o registro
  WRITE [tipo]          S, valor -> S; imprime no formato MPL e quebra linha
  TRAP [mensagem]       interrompe com erro de execucao na posicao anexada

CALL guarda locais, base da pilha e endereco de retorno explicitamente.
RETURN restaura a base e empilha o resultado, quando houver. Limites sao
da VM e independem de sys.getrecursionlimit().
"""
from dataclasses import dataclass, field
import json
import operator

from mplc.erros import ErroMPL


MAX_QUADROS = 4096
MAX_OPERANDOS = 65536
_TIPOS = {'inteiro': int, 'real': float, 'logico': bool, 'texto': str}
_OPERACOES = {
    '+': operator.add, '-': operator.sub, '*': operator.mul,
    '==': operator.eq, '!=': operator.ne, '<': operator.lt,
    '<=': operator.le, '>': operator.gt, '>=': operator.ge,
    'e': operator.and_, 'ou': operator.or_,
}
_ARGUMENTOS = {
    'PUSH': (object,), 'LOAD': (str,), 'STORE': (str,), 'I2R': (),
    'BINARY': (str, str), 'UNARY': (str, str), 'LABEL': (str,),
    'JUMP': (str,), 'JUMP_FALSE': (str,), 'CALL': (str, int),
    'RETURN': (bool,), 'WRITE': (str,), 'TRAP': (str,),
}


@dataclass
class _Funcao:
    tipo: str
    parametros: list
    codigo: list = field(default_factory=list)
    rotulos: dict = field(default_factory=dict)


@dataclass
class RegistroAtivacao:
    funcao: _Funcao
    locais: dict
    base: int
    retorno: int
    pc: int = 0


def _erro(pos, mensagem):
    # Ate um bytecode editado com TRAP contendo '\n' respeita stderr em uma linha.
    return ErroMPL('execucao', pos[0], pos[1], ' '.join(str(mensagem).splitlines()))


def _carregar(texto):
    linhas = texto.splitlines()
    if not linhas or linhas[0] != 'MPLB 1':
        raise _erro((1, 1), 'cabecalho invalido: esperado MPLB 1')
    funcoes, atual = {}, None
    for numero, linha in enumerate(linhas[1:], 2):
        linha = linha.strip()
        if not linha:
            continue
        pos = (numero, 1)
        try:
            if linha.startswith('FUNC '):
                dados = json.loads(linha[5:])
                if not isinstance(dados, list) or len(dados) != 3:
                    raise ValueError('diretiva FUNC invalida')
                nome, tipo, parametros = dados
                if (atual is not None or type(nome) is not str or nome in funcoes
                        or type(tipo) is not str or tipo not in (*_TIPOS, 'vazio')
                        or type(parametros) is not list
                        or any(type(p) is not str for p in parametros)
                        or len(set(parametros)) != len(parametros)):
                    raise ValueError('assinatura de funcao invalida')
                atual = _Funcao(tipo, parametros)
                funcoes[nome] = atual
            elif linha == 'END':
                if atual is None or not atual.codigo:
                    raise ValueError('END sem funcao ou funcao sem instrucoes')
                atual = None
            else:
                origem, op, dados = linha.split(maxsplit=2)
                l, c = origem.split(':')
                pos = (int(l), int(c))
                if min(pos) < 1 or atual is None:
                    raise ValueError('instrucao fora de funcao ou posicao invalida')
                args = json.loads(dados)
                assinatura = _ARGUMENTOS.get(op)
                if (assinatura is None or type(args) is not list
                        or len(args) != len(assinatura)
                        or any(t is not object and type(a) is not t
                               for a, t in zip(args, assinatura))):
                    raise ValueError('opcode ou argumentos invalidos')
                if op == 'PUSH' and type(args[0]) not in (int, float, bool, str):
                    raise ValueError('PUSH exige literal escalar')
                if op == 'CALL' and args[1] < 0:
                    raise ValueError('quantidade de argumentos negativa')
                if op == 'LABEL':
                    if args[0] in atual.rotulos:
                        raise ValueError('rotulo duplicado')
                    atual.rotulos[args[0]] = len(atual.codigo)
                atual.codigo.append((op, args, pos))
        except (ValueError, TypeError, KeyError, RecursionError) as erro:
            raise _erro(pos, f'bytecode invalido: {erro}') from None
    if atual is not None:
        raise _erro((len(linhas), 1), 'funcao sem END')
    principal = funcoes.get('principal')
    if principal is None or principal.parametros or principal.tipo != 'vazio':
        raise _erro((1, 1), 'esperado principal sem parametros e de retorno vazio')
    for funcao in funcoes.values():
        for op, args, pos in funcao.codigo:
            if op in ('JUMP', 'JUMP_FALSE') and args[0] not in funcao.rotulos:
                raise _erro(pos, f'rotulo inexistente: {args[0]}')
            if op == 'CALL':
                alvo = funcoes.get(args[0])
                if alvo is None or len(alvo.parametros) != args[1]:
                    raise _erro(pos, 'chamada com funcao ou quantidade de argumentos invalida')
    return funcoes


def _conferir_tipo(valor, tipo):
    if tipo not in _TIPOS or type(valor) is not _TIPOS[tipo]:
        raise ValueError(f'operando incompativel com {tipo}')


def _binario(op, tipo, a, b):
    _conferir_tipo(a, tipo)
    _conferir_tipo(b, tipo)
    if op in ('e', 'ou'):
        valido = tipo == 'logico'
    elif op in ('==', '!='):
        valido = True
    elif op == '+':
        valido = tipo in ('inteiro', 'real', 'texto')
    elif op == '%':
        valido = tipo == 'inteiro'
    else:
        valido = tipo in ('inteiro', 'real')
    if not valido:
        raise ValueError(f'operacao {op} invalida para {tipo}')
    if op in ('/', '%'):
        if b == 0:
            raise ZeroDivisionError('resto por zero' if op == '%' else 'divisao por zero')
        if tipo == 'inteiro':
            # Nunca passa por float: preserva inteiros acima de 2**53.
            quociente = abs(a) // abs(b)
            if (a < 0) != (b < 0):
                quociente = -quociente
            return a - quociente * b if op == '%' else quociente
        return a / b
    if op not in _OPERACOES:
        raise ValueError(f'operador binario desconhecido: {op}')
    return _OPERACOES[op](a, b)


def executar(texto_mplb, saida):
    """Executa somente instrucoes; chamadas MPL nao usam recursao Python."""
    funcoes = _carregar(texto_mplb)
    pilha = []
    registros = [RegistroAtivacao(funcoes['principal'], {}, 0, -1)]

    def retirar(registro):
        if len(pilha) <= registro.base:
            raise ValueError('pilha de operandos vazia')
        return pilha.pop()

    while registros:
        registro = registros[-1]
        if registro.pc >= len(registro.funcao.codigo):
            pos = registro.funcao.codigo[-1][2]
            raise _erro(pos, 'funcao terminou sem RETURN')
        op, args, pos = registro.funcao.codigo[registro.pc]
        registro.pc += 1
        try:
            if op == 'PUSH':
                pilha.append(args[0])
            elif op == 'LOAD':
                if args[0] not in registro.locais:
                    raise ValueError(f'slot nao inicializado: {args[0]}')
                pilha.append(registro.locais[args[0]])
            elif op == 'STORE':
                registro.locais[args[0]] = retirar(registro)
            elif op == 'I2R':
                valor = retirar(registro)
                _conferir_tipo(valor, 'inteiro')
                pilha.append(float(valor))
            elif op == 'BINARY':
                direita, esquerda = retirar(registro), retirar(registro)
                pilha.append(_binario(args[0], args[1], esquerda, direita))
            elif op == 'UNARY':
                valor = retirar(registro)
                operador, tipo = args
                _conferir_tipo(valor, tipo)
                if operador == 'nao' and tipo == 'logico':
                    pilha.append(not valor)
                elif operador == '-' and tipo in ('inteiro', 'real'):
                    pilha.append(-valor)
                else:
                    raise ValueError('operacao unaria invalida')
            elif op == 'LABEL':
                pass
            elif op == 'JUMP':
                registro.pc = registro.funcao.rotulos[args[0]]
            elif op == 'JUMP_FALSE':
                condicao = retirar(registro)
                _conferir_tipo(condicao, 'logico')
                if not condicao:
                    registro.pc = registro.funcao.rotulos[args[0]]
            elif op == 'CALL':
                if len(registros) >= MAX_QUADROS:
                    raise _erro(pos, 'estouro de pilha de chamadas')
                nome, quantidade = args
                if len(pilha) - registro.base < quantidade:
                    raise ValueError('faltam argumentos na pilha')
                base = len(pilha) - quantidade
                argumentos = pilha[base:]
                del pilha[base:]
                funcao = funcoes[nome]
                locais = dict(zip(funcao.parametros, argumentos))
                registros.append(RegistroAtivacao(funcao, locais, base, registro.pc))
            elif op == 'RETURN':
                tem_valor = args[0]
                if tem_valor != (registro.funcao.tipo != 'vazio'):
                    raise ValueError('RETURN incompativel com o retorno da funcao')
                valor = retirar(registro) if tem_valor else None
                if tem_valor:
                    _conferir_tipo(valor, registro.funcao.tipo)
                del pilha[registro.base:]
                registros.pop()
                if registros:
                    registros[-1].pc = registro.retorno
                    if tem_valor:
                        pilha.append(valor)
            elif op == 'WRITE':
                valor = retirar(registro)
                _conferir_tipo(valor, args[0])
                if args[0] == 'real':
                    texto = f'{valor:.6f}'
                elif args[0] == 'logico':
                    texto = 'verdadeiro' if valor else 'falso'
                else:
                    texto = str(valor)
                saida.write(texto + '\n')
            elif op == 'TRAP':
                raise _erro(pos, args[0])
            if len(pilha) > MAX_OPERANDOS:
                raise _erro(pos, 'estouro de pilha de operandos')
        except ZeroDivisionError as erro:
            raise _erro(pos, erro) from None
        except OverflowError:
            raise _erro(pos, 'estouro numerico') from None
        except MemoryError:
            raise _erro(pos, 'memoria esgotada') from None
        except (ValueError, TypeError, KeyError, IndexError) as erro:
            raise _erro(pos, f'bytecode invalido: {erro}') from None
