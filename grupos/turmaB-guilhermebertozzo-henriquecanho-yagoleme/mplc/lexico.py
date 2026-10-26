"""
Entrega 1 — analise lexica.

Transformar o texto do programa numa lista de tokens.

O que voces tem que devolver: uma lista de Token. O ultimo elemento e sempre
um token FIM_ARQUIVO. A regra de posicao dele esta em CONTRATOS.md, secao 7.

Leiam antes: LINGUAGEM.md secao 2, e CONTRATOS.md secao 2.
"""
from mplc.erros import ErroMPL


RESERVADAS = {
    'funcao': 'FUNCAO', 'retorne': 'RETORNE', 'se': 'SE', 'senao': 'SENAO',
    'enquanto': 'ENQUANTO', 'escreva': 'ESCREVA',
    'inteiro': 'TIPO_INTEIRO', 'real': 'TIPO_REAL', 'logico': 'TIPO_LOGICO',
    'texto': 'TIPO_TEXTO', 'vazio': 'TIPO_VAZIO',
    'verdadeiro': 'LOGICO', 'falso': 'LOGICO', 'e': 'E', 'ou': 'OU', 'nao': 'NAO',
}
SIMBOLOS = {
    '+': 'MAIS', '-': 'MENOS', '*': 'VEZES', '/': 'DIVIDE', '%': 'RESTO',
    '==': 'IGUAL', '!=': 'DIFERENTE', '<': 'MENOR', '<=': 'MENOR_IGUAL',
    '>': 'MAIOR', '>=': 'MAIOR_IGUAL', '=': 'ATRIBUI',
    '(': 'ABRE_PAR', ')': 'FECHA_PAR', '{': 'ABRE_CHAVE', '}': 'FECHA_CHAVE',
    ',': 'VIRGULA', ';': 'PONTO_VIRGULA',
}
# Compartilhado com o parser: decodificar apenas os quatro escapes da MPL.
ESCAPES = {'n': '\n', 't': '\t', '"': '"', '\\': '\\'}


def _letra(c):
    return 'a' <= c <= 'z' or 'A' <= c <= 'Z' or c == '_'


def _digito(c):
    return '0' <= c <= '9'


class Token:
    __slots__ = ('tipo', 'lexema', 'linha', 'coluna')

    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo = tipo          # 'ID', 'INTEIRO', 'MAIS', ... (a lista esta no contrato)
        self.lexema = lexema      # o texto exato como apareceu no fonte
        self.linha = linha
        self.coluna = coluna      # a coluna do PRIMEIRO caractere do token

    def __str__(self):
        # esta e a linha que o --tokens imprime; nao mexam no formato
        return f"{self.linha},{self.coluna},{self.tipo},{self.lexema}"


def analisar(fonte):
    """Recebe o texto do programa. Devolve a lista de Token."""
    tokens = []
    i, linha, coluna = 0, 1, 1
    tamanho = len(fonte)

    def avancar():
        nonlocal i, linha, coluna
        if fonte[i] == '\n':
            linha += 1
            coluna = 1
        else:
            coluna += 1
        i += 1

    while i < tamanho:
        c = fonte[i]
        if c in ' \t\r\n':
            avancar()
            continue

        inicio, linha_inicio, coluna_inicio = i, linha, coluna
        if fonte.startswith('//', i):
            while i < tamanho and fonte[i] not in '\r\n':
                avancar()
            continue
        if fonte.startswith('/*', i):
            avancar()
            avancar()
            while i < tamanho and not fonte.startswith('*/', i):
                avancar()
            if i == tamanho:
                raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                              'comentario de bloco nao fechado')
            avancar()
            avancar()
            continue

        if _letra(c):
            avancar()
            while i < tamanho and (_letra(fonte[i]) or _digito(fonte[i])):
                avancar()
            tipo = RESERVADAS.get(fonte[inicio:i], 'ID')
        elif _digito(c):
            while i < tamanho and _digito(fonte[i]):
                avancar()
            tipo = 'INTEIRO'
            if i < tamanho and fonte[i] == '.':
                if i + 1 == tamanho or not _digito(fonte[i + 1]):
                    raise ErroMPL('lexico', linha, coluna,
                                  'o ponto de um real exige digitos dos dois lados')
                avancar()
                while i < tamanho and _digito(fonte[i]):
                    avancar()
                tipo = 'REAL'
        elif c == '"':
            avancar()
            while i < tamanho and fonte[i] not in '"\r\n':
                if fonte[i] == '\\':
                    if i + 1 == tamanho or fonte[i + 1] in '\r\n':
                        raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                                      'literal de texto nao fechado')
                    if fonte[i + 1] not in ESCAPES:
                        raise ErroMPL('lexico', linha, coluna,
                                      'escape de texto invalido: ' + repr(fonte[i:i + 2]))
                    avancar()
                avancar()
            if i == tamanho or fonte[i] != '"':
                raise ErroMPL('lexico', linha_inicio, coluna_inicio,
                              'literal de texto nao fechado')
            avancar()
            tipo = 'TEXTO'
        else:
            # Maior casamento: os operadores duplos precedem os simples.
            simbolo = fonte[i:i + 2]
            if simbolo not in SIMBOLOS:
                simbolo = c
            if simbolo not in SIMBOLOS:
                raise ErroMPL('lexico', linha, coluna,
                              'caractere invalido: ' + repr(c))
            tipo = SIMBOLOS[simbolo]
            for _ in simbolo:
                avancar()
        tokens.append(Token(tipo, fonte[inicio:i], linha_inicio, coluna_inicio))

    tokens.append(Token('FIM_ARQUIVO', '', linha, coluna))
    return tokens
