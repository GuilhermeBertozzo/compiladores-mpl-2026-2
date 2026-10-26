"""
Entrega 2 — analise sintatica.

Transformar a lista de tokens numa arvore.

Sugestao forte: descida recursiva, uma funcao por nivel de precedencia, na
ordem da secao 3.3 da especificacao. E como voces vao enxergar a precedencia
virar formato de arvore.

Gerador de parser (ANTLR, PLY, yacc) esta proibido nesta entrega e na
anterior — o objetivo e entender, e o gerador esconde exatamente a parte
que esta sendo ensinada.

Leiam antes: LINGUAGEM.md secoes 3 a 5, e CONTRATOS.md secao 3.
"""
from mplc.erros import ErroMPL
from mplc.lexico import ESCAPES


TIPOS = {'TIPO_INTEIRO', 'TIPO_REAL', 'TIPO_LOGICO', 'TIPO_TEXTO'}


class No:
    """AST compartilhada pelas fases, com rotulos definidos no contrato.

    Todo extra tem kind (primeira palavra do rotulo). Nos nomeados tem nome;
    funcao, parametro, declaracao e literal tem tipo; literal tem valor Python
    decodificado; binario e unario tem op. Tipos de expressoes nao literais
    ficam para a semantica. A posicao aponta o token inicial da construcao,
    ou o operador em operacoes. Parametros aponta o '(' e programa aponta
    o primeiro token (inclusive EOF no programa vazio).
    """

    def __init__(self, rotulo, filhos=None, linha=0, coluna=0, **extra):
        self.rotulo = rotulo      # 'binario +', 'literal inteiro 1', 'bloco', ...
        self.filhos = filhos or []
        self.linha = linha
        self.coluna = coluna
        self.extra = extra        # o que a semantica quiser pendurar depois
        self.extra['kind'] = rotulo.split()[0]


def analisar(tokens):
    """Recebe a lista de Token. Devolve a raiz da arvore (um No 'programa')."""
    return _Parser(tokens).programa()


class _Parser:
    """Descida recursiva; recebe os tokens terminados em FIM_ARQUIVO do lexico.

    programa = funcao* EOF
    funcao = 'funcao' tipo_retorno ID '(' parametros? ')' bloco
    parametros = tipo ID (',' tipo ID)*
    bloco = '{' comando* '}'
    comando = tipo ID ('=' expressao)? ';' | ID '=' expressao ';'
            | chamada ';' | 'retorne' expressao? ';' | bloco
            | 'escreva' '(' expressao ')' ';'
            | 'se' '(' expressao ')' bloco ('senao' bloco)?
            | 'enquanto' '(' expressao ')' bloco

    Cada nivel binario usa um laco, garantindo associatividade a esquerda.
    Unarios sao empilhados e montados ao contrario (associatividade a direita).
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.indice = 0

    @property
    def atual(self):
        return self.tokens[self.indice]

    def avancar(self):
        token = self.atual
        if token.tipo != 'FIM_ARQUIVO':
            self.indice += 1
        return token

    def aceitar(self, tipo):
        if self.atual.tipo == tipo:
            return self.avancar()
        return None

    def erro(self, esperado):
        token = self.atual
        encontrado = repr(token.lexema) if token.lexema else 'fim do arquivo'
        raise ErroMPL('sintatico', token.linha, token.coluna,
                      f'esperado {esperado}; encontrado {encontrado}')

    def exigir(self, tipo):
        token = self.aceitar(tipo)
        if token is None:
            self.erro(tipo)
        return token

    @staticmethod
    def no(rotulo, token, filhos=None, **extra):
        return No(rotulo, filhos, token.linha, token.coluna, **extra)

    def tipo(self, retorno=False):
        if self.atual.tipo in TIPOS or (retorno and self.atual.tipo == 'TIPO_VAZIO'):
            return self.avancar()
        self.erro('tipo de retorno' if retorno else 'tipo inteiro, real, logico ou texto')

    def programa(self):
        inicio = self.atual
        funcoes = []
        while self.atual.tipo != 'FIM_ARQUIVO':
            funcoes.append(self.funcao())
        return self.no('programa', inicio, funcoes)

    def funcao(self):
        inicio = self.exigir('FUNCAO')
        tipo = self.tipo(retorno=True).lexema
        nome = self.exigir('ID').lexema
        abertura = self.exigir('ABRE_PAR')
        parametros = []
        if self.atual.tipo != 'FECHA_PAR':
            while True:
                tipo_parametro = self.tipo()
                nome_parametro = self.exigir('ID').lexema
                parametros.append(self.no(
                    f'parametro {nome_parametro} {tipo_parametro.lexema}', tipo_parametro,
                    nome=nome_parametro, tipo=tipo_parametro.lexema))
                if not self.aceitar('VIRGULA'):
                    break
        self.exigir('FECHA_PAR')
        lista = self.no('parametros', abertura, parametros)
        corpo = self.bloco()
        return self.no(f'funcao {nome} {tipo}', inicio, [lista, corpo], nome=nome, tipo=tipo)

    def bloco(self):
        inicio = self.exigir('ABRE_CHAVE')
        comandos = []
        while self.atual.tipo != 'FECHA_CHAVE':
            if self.atual.tipo == 'FIM_ARQUIVO':
                self.erro('FECHA_CHAVE')
            comandos.append(self.comando())
        self.exigir('FECHA_CHAVE')
        return self.no('bloco', inicio, comandos)

    def comando(self):
        inicio = self.atual
        if inicio.tipo == 'ABRE_CHAVE':
            return self.bloco()
        if inicio.tipo in TIPOS:
            tipo = self.tipo().lexema
            nome = self.exigir('ID').lexema
            filhos = [self.expressao()] if self.aceitar('ATRIBUI') else []
            self.exigir('PONTO_VIRGULA')
            return self.no(f'declaracao {nome} {tipo}', inicio, filhos, nome=nome, tipo=tipo)
        if inicio.tipo == 'ID':
            self.avancar()
            if self.aceitar('ATRIBUI'):
                no = self.no(f'atribuicao {inicio.lexema}', inicio,
                             [self.expressao()], nome=inicio.lexema)
            elif self.atual.tipo == 'ABRE_PAR':
                no = self.chamada(inicio)
            else:
                self.erro('ATRIBUI ou ABRE_PAR')
            self.exigir('PONTO_VIRGULA')
            return no
        if inicio.tipo in {'SE', 'ENQUANTO'}:
            self.avancar()
            self.exigir('ABRE_PAR')
            condicao = self.expressao()
            self.exigir('FECHA_PAR')
            filhos = [condicao, self.bloco()]
            if inicio.tipo == 'SE' and self.aceitar('SENAO'):
                filhos.append(self.bloco())
            return self.no(inicio.lexema, inicio, filhos)
        if inicio.tipo == 'ESCREVA':
            self.avancar()
            self.exigir('ABRE_PAR')
            valor = self.expressao()
            self.exigir('FECHA_PAR')
            self.exigir('PONTO_VIRGULA')
            return self.no('escreva', inicio, [valor])
        if inicio.tipo == 'RETORNE':
            self.avancar()
            filhos = [] if self.atual.tipo == 'PONTO_VIRGULA' else [self.expressao()]
            self.exigir('PONTO_VIRGULA')
            return self.no('retorne', inicio, filhos)
        self.erro('comando')

    def chamada(self, nome):
        self.exigir('ABRE_PAR')
        argumentos = []
        if self.atual.tipo != 'FECHA_PAR':
            argumentos.append(self.expressao())
            while self.aceitar('VIRGULA'):
                argumentos.append(self.expressao())
        self.exigir('FECHA_PAR')
        return self.no(f'chamada {nome.lexema}', nome, argumentos, nome=nome.lexema)

    def binarios(self, seguinte, operadores):
        esquerda = seguinte()
        while self.atual.tipo in operadores:
            operador = self.avancar()
            direita = seguinte()
            esquerda = self.no(f'binario {operador.lexema}', operador,
                               [esquerda, direita], op=operador.lexema)
        return esquerda

    def expressao(self):
        return self.ou()

    def ou(self):
        return self.binarios(self.e, {'OU'})

    def e(self):
        return self.binarios(self.igualdade, {'E'})

    def igualdade(self):
        return self.binarios(self.relacao, {'IGUAL', 'DIFERENTE'})

    def relacao(self):
        return self.binarios(self.adicao, {'MENOR', 'MENOR_IGUAL', 'MAIOR', 'MAIOR_IGUAL'})

    def adicao(self):
        return self.binarios(self.multiplicacao, {'MAIS', 'MENOS'})

    def multiplicacao(self):
        return self.binarios(self.unario, {'VEZES', 'DIVIDE', 'RESTO'})

    def unario(self):
        operadores = []
        while self.atual.tipo in {'MENOS', 'NAO'}:
            operadores.append(self.avancar())
        no = self.primario()
        for operador in reversed(operadores):
            no = self.no(f'unario {operador.lexema}', operador, [no], op=operador.lexema)
        return no

    def primario(self):
        token = self.atual
        if self.aceitar('ABRE_PAR'):
            no = self.expressao()
            self.exigir('FECHA_PAR')
            return no
        if self.aceitar('ID'):
            if self.atual.tipo == 'ABRE_PAR':
                return self.chamada(token)
            return self.no(f'variavel {token.lexema}', token, nome=token.lexema)
        if token.tipo not in {'INTEIRO', 'REAL', 'LOGICO', 'TEXTO'}:
            self.erro('literal, identificador ou expressao entre parenteses')
        self.avancar()
        tipo = token.tipo.lower()
        if token.tipo == 'INTEIRO':
            valor = int(token.lexema)
            representacao = str(valor)
        elif token.tipo == 'REAL':
            valor = float(token.lexema)
            representacao = f'{valor:.6f}'
        elif token.tipo == 'LOGICO':
            valor = token.lexema == 'verdadeiro'
            representacao = token.lexema
        else:
            caracteres = []
            i = 1
            while i < len(token.lexema) - 1:
                c = token.lexema[i]
                if c == '\\':
                    i += 1
                    c = ESCAPES[token.lexema[i]]
                caracteres.append(c)
                i += 1
            valor = ''.join(caracteres)
            representacao = token.lexema
        return self.no(f'literal {tipo} {representacao}', token, tipo=tipo, valor=valor)


def despejar(no, nivel=0, saida=None):
    """Imprime a arvore no formato do --ast. Ja esta pronto: dois espacos por nivel."""
    saida = saida if saida is not None else []
    saida.append('  ' * nivel + no.rotulo)
    for f in no.filhos:
        despejar(f, nivel + 1, saida)
    return saida
