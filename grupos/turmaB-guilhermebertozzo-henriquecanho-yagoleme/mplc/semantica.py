"""
Entrega 3 — analise semantica.

Tabela de simbolos, escopos aninhados e verificacao de tipos.

Tres coisas que costumam ser esquecidas e valem nota:
  - o corpo de uma funcao abre DOIS escopos (o dos parametros e o do bloco);
  - uma funcao pode ser chamada antes de aparecer no arquivo, entao a
    primeira passada so coleta assinaturas;
  - funcao com retorno declarado precisa garantir o retorno em TODOS os
    caminhos.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 4.
"""
from dataclasses import dataclass, field
from mplc.erros import ErroMPL


@dataclass
class Simbolo:
    nome: str
    categoria: str
    tipo: str
    linha: int
    parametros: list = field(default_factory=list)
    slot: str = ''


@dataclass
class Escopo:
    numero: int
    descricao: str
    pai: object = None
    simbolos: dict = field(default_factory=dict)

    def buscar(self, nome):
        atual = self
        while atual is not None:
            if nome in atual.simbolos:
                return atual.simbolos[nome]
            atual = atual.pai
        return None


def erro(no, mensagem):
    raise ErroMPL('semantico', no.linha or 1, no.coluna or 1, mensagem)


def cabe(origem, destino):
    return origem == destino or (origem == 'inteiro' and destino == 'real')


class Analisador:
    def __init__(self):
        self.escopos = [Escopo(0, 'global')]
        self.atual = self.escopos[0]
        self.retorno = 'vazio'

    def abrir(self, descricao):
        novo = Escopo(len(self.escopos), descricao, self.atual)
        self.escopos.append(novo)
        self.atual = novo
        return novo

    def declarar(self, no, categoria, parametros=None):
        nome, tipo = no.extra['nome'], no.extra['tipo']
        if nome in self.atual.simbolos:
            erro(no, f'{nome!r} já foi declarado neste escopo')
        simbolo = Simbolo(nome, categoria, tipo, no.linha, parametros or [])
        if categoria != 'funcao':
            if tipo == 'vazio':
                erro(no, 'variável ou parâmetro não pode ter tipo vazio')
            simbolo.slot = f'v{self.atual.numero}_{nome}'
            no.extra['slot'] = simbolo.slot
        self.atual.simbolos[nome] = simbolo
        return simbolo

    def analisar(self, arvore):
        # Registra assinaturas antes dos corpos, permitindo recursão mútua.
        for funcao in arvore.filhos:
            tipos = [p.extra['tipo'] for p in funcao.filhos[0].filhos]
            self.declarar(funcao, 'funcao', tipos)
        principal = self.atual.simbolos.get('principal')
        if principal is None:
            erro(arvore, 'falta funcao vazio principal()')
        if principal.tipo != 'vazio' or principal.parametros:
            no = next(f for f in arvore.filhos if f.extra['nome'] == 'principal')
            erro(no, 'principal deve retornar vazio e não receber parâmetros')
        for funcao in arvore.filhos:
            self.abrir('funcao ' + funcao.extra['nome'])
            self.retorno = funcao.extra['tipo']
            for parametro in funcao.filhos[0].filhos:
                self.declarar(parametro, 'parametro')
            retorna = self.comando(funcao.filhos[1])
            if self.retorno != 'vazio' and not retorna:
                erro(funcao, 'a função precisa retornar em todos os caminhos')
            self.atual = self.atual.pai
        return self.escopos

    def variavel(self, no):
        simbolo = self.atual.buscar(no.extra['nome'])
        if simbolo is None or simbolo.categoria == 'funcao':
            erro(no, f'variável {no.extra["nome"]!r} não declarada')
        no.extra.update(tipo=simbolo.tipo, slot=simbolo.slot)
        return simbolo.tipo

    def exigir(self, no, origem, destino):
        if not cabe(origem, destino):
            erro(no, f'esperado {destino}, recebido {origem}')

    def comando(self, no):
        """Devolve se o comando garante retorno em todos os caminhos."""
        kind = no.extra['kind']
        if kind == 'bloco':
            self.abrir('bloco')
            retorna = False
            for filho in no.filhos:
                # Mesmo código inalcançável deve ser semanticamente válido.
                garante = self.comando(filho)
                retorna = retorna or garante
            self.atual = self.atual.pai
            return retorna
        if kind == 'declaracao':
            if no.extra['nome'] in self.atual.simbolos:
                erro(no, 'nome já declarado neste escopo')
            if no.filhos:
                self.exigir(no, self.expressao(no.filhos[0]), no.extra['tipo'])
            self.declarar(no, 'variavel')
        elif kind == 'atribuicao':
            destino = self.variavel(no)
            self.exigir(no, self.expressao(no.filhos[0]), destino)
        elif kind == 'escreva':
            self.expressao(no.filhos[0])
        elif kind == 'chamada':
            self.expressao(no, permite_vazio=True)
        elif kind in ('se', 'enquanto'):
            self.exigir(no.filhos[0], self.expressao(no.filhos[0]), 'logico')
            entao = self.comando(no.filhos[1])
            senao = self.comando(no.filhos[2]) if len(no.filhos) == 3 else False
            return kind == 'se' and entao and senao
        elif kind == 'retorne':
            no.extra['destino_tipo'] = self.retorno
            if self.retorno == 'vazio':
                if no.filhos:
                    erro(no, 'função vazio só permite retorne sem valor')
            else:
                if not no.filhos:
                    erro(no, f'retorne precisa de um valor {self.retorno}')
                self.exigir(no, self.expressao(no.filhos[0]), self.retorno)
            return True
        else:
            raise ValueError(f'nó de comando desconhecido: {kind}')
        return False

    def expressao(self, no, permite_vazio=False):
        kind = no.extra['kind']
        if kind == 'literal':
            tipo = no.extra['tipo']
        elif kind == 'variavel':
            tipo = self.variavel(no)
        elif kind == 'chamada':
            funcao = self.atual.buscar(no.extra['nome'])
            if funcao is None or funcao.categoria != 'funcao':
                erro(no, f'função {no.extra["nome"]!r} não declarada')
            if len(no.filhos) != len(funcao.parametros):
                erro(no, f'esperados {len(funcao.parametros)} argumentos, recebidos {len(no.filhos)}')
            for argumento, esperado in zip(no.filhos, funcao.parametros):
                self.exigir(argumento, self.expressao(argumento), esperado)
            tipo = funcao.tipo
            no.extra['param_tipos'] = list(funcao.parametros)
        elif kind == 'unario':
            operando = self.expressao(no.filhos[0])
            op = no.extra['op']
            if op == 'nao':
                self.exigir(no, operando, 'logico')
                tipo = 'logico'
            else:
                if operando not in ('inteiro', 'real'):
                    erro(no, 'menos unário exige número')
                tipo = operando
        elif kind == 'binario':
            esquerda = self.expressao(no.filhos[0])
            direita = self.expressao(no.filhos[1])
            op = no.extra['op']
            numericos = esquerda in ('inteiro', 'real') and direita in ('inteiro', 'real')
            if op in ('e', 'ou'):
                self.exigir(no, esquerda, 'logico')
                self.exigir(no, direita, 'logico')
                tipo = 'logico'
            elif op in ('==', '!='):
                if esquerda != direita and not numericos:
                    erro(no, 'igualdade exige tipos compatíveis')
                tipo = 'logico'
            elif op in ('<', '<=', '>', '>='):
                if not numericos:
                    erro(no, 'comparação de ordem exige números')
                tipo = 'logico'
            elif op == '%':
                if esquerda != 'inteiro' or direita != 'inteiro':
                    erro(no, 'resto exige dois inteiros')
                tipo = 'inteiro'
            elif op == '+' and esquerda == direita == 'texto':
                tipo = 'texto'
            else:
                if not numericos:
                    erro(no, f'operador {op} exige números compatíveis')
                tipo = 'real' if 'real' in (esquerda, direita) else 'inteiro'
        else:
            raise ValueError(f'nó de expressão desconhecido: {kind}')
        if tipo == 'vazio' and not permite_vazio:
            erro(no, 'chamada vazio não pode ser usada como expressão')
        no.extra['tipo'] = tipo
        return tipo


def analisar(arvore):
    return Analisador().analisar(arvore)


def despejar(tabela):
    linhas = []
    for escopo in tabela:
        cabecalho = f'escopo {escopo.numero} {escopo.descricao}'
        if escopo.pai is not None:
            cabecalho += f' pai {escopo.pai.numero}'
        linhas.append(cabecalho)
        for simbolo in escopo.simbolos.values():
            tipo = simbolo.tipo
            if simbolo.categoria == 'funcao':
                tipo += '(' + ','.join(simbolo.parametros) + ')'
            linhas.append(f'  {simbolo.nome}|{simbolo.categoria}|{tipo}|{simbolo.linha}')
    return linhas
