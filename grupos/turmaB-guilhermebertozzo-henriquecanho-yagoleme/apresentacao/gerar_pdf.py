"""Gera o PDF dos slides; ferramenta opcional, separada do compilador.

Uso: python3 apresentacao/gerar_pdf.py
Dependência exclusiva desta ferramenta: reportlab.
"""
from html import escape
from io import StringIO
from pathlib import Path
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from mplc import lexico, sintatico, semantica, intermediario, gerador, vm
from mplc.erros import ErroMPL
from mplc.principal import compilar_ate

DESTINO = Path(__file__).resolve().parent
AZUL = HexColor('#132B43')
VERDE = HexColor('#087C71')
CINZA = HexColor('#4C5C68')
LARGURA, ALTURA = 960, 540


def rastrear():
    fonte = (RAIZ / 'exemplos/torre_hanoi.mpl').read_text(encoding='utf-8')
    linha = next(i for i, texto in enumerate(fonte.splitlines(), 1)
                 if 'passos = 2 * 3 + 1;' in texto)
    tokens = lexico.analisar(fonte)
    arvore = sintatico.analisar(tokens)
    tabela = semantica.analisar(arvore)
    codigo = intermediario.gerar(arvore, tabela)
    bytecode = gerador.gerar(codigo)
    saida = StringIO()
    vm.executar('\n'.join(bytecode), saida)
    esperado = (RAIZ / 'exemplos/torre_hanoi.saida').read_text(encoding='utf-8')
    assert saida.getvalue() == esperado, 'A demonstração precisa estar correta.'
    funcao = next(f for f in codigo.funcoes if f.nome == 'principal')
    trecho = intermediario.Codigo([intermediario.Funcao(
        funcao.nome, funcao.tipo, funcao.parametros,
        [i for i in funcao.instrucoes if i.linha == linha])])
    ir = intermediario.despejar(trecho)[1:-1]
    instrucoes = [s for s in bytecode if s.startswith(f'{linha}:')]
    principal = next(n for n in arvore.filhos if n.extra['nome'] == 'principal')
    atribuicao = next(n for n in principal.filhos[1].filhos
                      if n.extra['kind'] == 'atribuicao')
    ast = sintatico.despejar(atribuicao)
    return linha, tokens, tabela, ir, instrucoes, ast, saida.getvalue()


def reproduzir_defeito():
    # Reproduz a serialização anterior sem alterar a implementação entregue.
    fonte = 'funcao vazio principal(){\n  escreva("A\u2028B");\n}'
    bytecode = '\n'.join(compilar_ate(fonte, 'bytecode'))
    anterior = bytecode.replace(r'\u2028', '\u2028')
    try:
        vm.executar(anterior, StringIO())
    except ErroMPL as erro:
        sintoma = str(erro)
    else:
        raise AssertionError('A reprodução do formato anterior deveria falhar.')
    saida = StringIO()
    vm.executar(bytecode, saida)
    assert saida.getvalue() == 'A\u2028B\n'
    return sintoma


def criar_pdf():
    linha, tokens, tabela, ir, instrucoes, ast, saida = rastrear()
    sintoma = reproduzir_defeito()
    arquivo = DESTINO / 'apresentacao-grupo-07.pdf'
    c = Canvas(str(arquivo), pagesize=(LARGURA, ALTURA))
    c.setTitle('Compilador MPL - Grupo 7 - Turma B')
    c.setAuthor('Grupo 7 - Turma B')
    c.setSubject('Compiladores: demonstração, fases, bytecode e defesa')
    numero = 0

    def texto(x, y, conteudo, tamanho=20, cor=AZUL, fonte='Helvetica'):
        c.setFillColor(cor)
        c.setFont(fonte, tamanho)
        for linha_texto in conteudo.split('\n'):
            c.drawString(x, y, linha_texto)
            y -= tamanho * 1.35
        return y

    def paragrafo(x, y, conteudo, largura=864, tamanho=20):
        estilo = ParagraphStyle('corpo', fontName='Helvetica', fontSize=tamanho,
                                leading=tamanho * 1.35, textColor=AZUL)
        p = Paragraph(escape(conteudo), estilo)
        w, h = p.wrap(largura, 500)
        assert y - h > 50, 'Texto ultrapassou a área útil do slide.'
        p.drawOn(c, x, y - h)
        return y - h - 16

    def codigo(x, y, linhas, tamanho=18):
        return texto(x, y, '\n'.join(linhas), tamanho, AZUL, 'Courier')

    def pagina(titulo, subtitulo=''):
        nonlocal numero
        if numero:
            c.showPage()
        numero += 1
        texto(48, 481, titulo, 32, AZUL, 'Helvetica-Bold')
        if subtitulo:
            texto(48, 445, subtitulo, 17, CINZA)
        texto(48, 24, 'Compiladores 2026-2  /  Grupo 7  /  Turma B', 11, CINZA)
        c.setFillColor(CINZA)
        c.setFont('Helvetica', 11)
        c.drawRightString(912, 24, str(numero))

    pagina('MPL em execução', 'Torre de Hanoi com três discos e sete movimentos')
    texto(48, 395, 'Henrique Motta Canho  ·  Guilherme Bertozzo', 18)
    texto(48, 369, 'Yago Leme', 18)
    codigo(48, 309, ['./compilar exemplos/torre_hanoi.mpl',
                     './executar exemplos/torre_hanoi.mplb'], 18)
    texto(48, 226, 'Duas funções recursivas', 23, VERDE, 'Helvetica-Bold')
    paragrafo(48, 198, 'hanoi imprime os movimentos. quantidade calcula o total. '
              'O programa compara esse total com uma expressão aritmética.', 470, 20)
    codigo(610, 308, ['A -> C', 'A -> B', 'C -> B', 'A -> C',
                      'B -> A', 'B -> C', 'A -> C'], 19)
    texto(610, 102, 'Total: 7', 22, VERDE, 'Helvetica-Bold')

    pagina('Tokens e árvore sintática', f'Linha {linha}: passos = 2 * 3 + 1;')
    texto(48, 397, 'Tokens com posição', 22, VERDE, 'Helvetica-Bold')
    codigo(48, 361, [str(t) for t in tokens if t.linha == linha], 18)
    texto(495, 397, 'Multiplicação antes da soma', 22, VERDE, 'Helvetica-Bold')
    codigo(495, 361, ast, 17)
    paragrafo(48, 108, 'O parser usa um nível por precedência. '
              'A soma fica na raiz e a multiplicação no filho esquerdo.', tamanho=19)

    pagina('Escopos e código intermediário', 'A semântica resolve o nome antes da geração')
    escopo = next(e for e in tabela if 'passos' in e.simbolos)
    simbolo = escopo.simbolos['passos']
    texto(48, 397, 'Símbolo da variável', 22, VERDE, 'Helvetica-Bold')
    codigo(48, 358, [f'escopo {escopo.numero} bloco pai {escopo.pai.numero}',
                      f'  passos|variavel|inteiro|{simbolo.linha}',
                      '', f'binding: {simbolo.slot}',
                      'slot no IR: v5'], 16)
    paragrafo(48, 211, 'O vínculo distingue variáveis de mesmo nome em blocos '
              'diferentes. O destino exige inteiro.', 390, 20)
    texto(510, 397, 'Uma operação por linha', 22, VERDE, 'Helvetica-Bold')
    codigo(510, 358, [s.strip() for s in ir], 19)
    paragrafo(510, 157, 't40 guarda 2 * 3. t42 soma 1. '
              'A cópia final grava 7 no slot de passos.', 380, 19)

    pagina('O arquivo executável .mplb', 'Instruções textuais com a posição do comando original')
    codigo(48, 400, instrucoes[:8], 19)
    codigo(510, 400, instrucoes[8:], 19)
    paragrafo(48, 128, 'PUSH empilha um literal. LOAD lê um slot. BINARY retira dois '
              'operandos e empilha o resultado. STORE grava o topo em um slot.', tamanho=21)

    pagina('Recursão na máquina virtual', 'Cada chamada conserva seu próprio estado')
    texto(48, 395, 'CALL cria um registro de ativação', 25, VERDE, 'Helvetica-Bold')
    paragrafo(48, 357, 'O registro guarda locais, parâmetros, base da pilha de '
              'operandos e endereço de retorno. A VM usa um laço iterativo.', tamanho=22)
    texto(48, 262, 'RETURN restaura o chamador', 25, VERDE, 'Helvetica-Bold')
    paragrafo(48, 224, 'O retorno remove o registro atual e devolve o valor, quando '
              'existe. Assim hanoi pode se chamar sem sobrescrever os dados da '
              'chamada anterior.', tamanho=22)
    texto(48, 92, 'Limite: 4096 registros. Estouro gera erro de execução.', 20, CINZA)

    pagina('Um separador Unicode quebrava o bytecode',
           'Caso reproduzível da implementação assistida')
    texto(48, 395, 'Sintoma', 23, VERDE, 'Helvetica-Bold')
    paragrafo(48, 362, 'Um texto com o caractere U+2028 compilava, mas a VM '
              'rejeitava o arquivo gerado.', tamanho=21)
    texto(48, 276, 'Diagnóstico', 23, VERDE, 'Helvetica-Bold')
    paragrafo(48, 243, 'A serialização conservava o caractere real. splitlines() '
              'interpretava U+2028 como outra linha e cortava a instrução PUSH.', tamanho=21)
    texto(48, 157, 'Correção e regressão', 23, VERDE, 'Helvetica-Bold')
    paragrafo(48, 124, 'JSON com ensure_ascii=True conserva uma instrução por linha. '
              'O teste confirma que o texto original volta intacto na saída.', tamanho=21)

    pagina('Preparação para a alteração ao vivo', 'Material de apoio após os cinco minutos')
    itens = [
        ('**', 'Lexer, precedência do parser, tipos e operação da VM'),
        ('senaose', 'Nova palavra reservada e encadeamento de nós se'),
        ('escreva(a, b)', 'Lista de argumentos, tipos e uma sequência de escrita'),
        ('pare', 'Contexto de laço na semântica e salto para o fim na IR'),
        ('e / ou', 'Desvios condicionais para executar o lado direito só se necessário'),
    ]
    y = 391
    for nome, descricao in itens:
        texto(48, y, nome, 21, VERDE, 'Helvetica-Bold')
        y = paragrafo(235, y + 18, descricao, 675, 19) - 6
    texto(48, 72, 'Dez minutos para implementar, três minutos para demonstrar.', 19, CINZA)

    pagina('Parser manual e gerador de parser', 'Comparação para a defesa')
    texto(48, 396, 'Implementação deste trabalho', 24, VERDE, 'Helvetica-Bold')
    paragrafo(48, 357, 'Funções Python reconhecem cada nível de precedência. '
              'É possível acompanhar diretamente o consumo de tokens e a montagem '
              'da árvore.', tamanho=22)
    texto(48, 248, 'Com um gerador', 24, VERDE, 'Helvetica-Bold')
    paragrafo(48, 209, 'Uma gramática declarativa alimentaria uma ferramenta, '
              'como ANTLR. Ainda seriam necessárias ações para montar a AST '
              'e as fases de semântica e geração.', tamanho=22)
    texto(48, 79, 'O enunciado exige implementação manual nas entregas 1 e 2.', 19, CINZA)
    c.save()
    rastreamento = ('Expressão na linha ' + str(linha) + '\n\nTOKENS\n'
                   + '\n'.join(str(t) for t in tokens if t.linha == linha)
                   + '\n\nAST\n' + '\n'.join(ast) + '\n\nTABELA\n'
                   + '\n'.join(semantica.despejar(tabela))
                   + '\n\nIR\n' + '\n'.join(ir) + '\n\nBYTECODE\n'
                   + '\n'.join(instrucoes) + '\n\nSAÍDA\n' + saida
                   + '\nREPRODUÇÃO DO DEFEITO ANTERIOR\n' + sintoma + '\n')
    (DESTINO / 'rastreamento.txt').write_text(rastreamento, encoding='utf-8')
    print(arquivo)


if __name__ == '__main__':
    criar_pdf()
