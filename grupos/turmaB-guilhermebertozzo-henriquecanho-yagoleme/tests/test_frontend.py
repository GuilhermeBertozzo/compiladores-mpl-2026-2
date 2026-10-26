"""Testes independentes do corpus: python3 -m unittest discover -s tests."""
import unittest

from mplc import lexico, sintatico
from mplc.erros import ErroMPL


def analisar(fonte):
    return sintatico.analisar(lexico.analisar(fonte))


def expressao(fonte):
    return analisar('funcao vazio f() { escreva(' + fonte + '); }').filhos[0].filhos[1].filhos[0].filhos[0]


def forma(no):
    return (no.rotulo, [forma(filho) for filho in no.filhos])


class LexicoTest(unittest.TestCase):
    def test_reservadas_identificadores_e_operadores(self):
        fonte = ('funcao retorne se senao enquanto escreva inteiro real logico texto vazio '
                 'verdadeiro falso e ou nao sePossivel _a9 Soma soma '
                 '+ - * / % == != < <= > >= = ( ) { } , ;')
        tipos = ('FUNCAO RETORNE SE SENAO ENQUANTO ESCREVA TIPO_INTEIRO TIPO_REAL '
                 'TIPO_LOGICO TIPO_TEXTO TIPO_VAZIO LOGICO LOGICO E OU NAO ID ID ID ID '
                 'MAIS MENOS VEZES DIVIDE RESTO IGUAL DIFERENTE MENOR MENOR_IGUAL '
                 'MAIOR MAIOR_IGUAL ATRIBUI ABRE_PAR FECHA_PAR ABRE_CHAVE FECHA_CHAVE '
                 'VIRGULA PONTO_VIRGULA FIM_ARQUIVO').split()
        tokens = lexico.analisar(fonte)
        self.assertEqual([t.tipo for t in tokens], tipos)
        self.assertEqual([t.lexema for t in tokens[:-1]], fonte.split())

    def test_posicoes_comentarios_e_fim(self):
        self.assertEqual([str(t) for t in lexico.analisar(' \tfoo/*x\ny*/<=2//fim\r\n')], [
            '1,3,ID,foo', '2,4,MENOR_IGUAL,<=', '2,6,INTEIRO,2',
            '3,1,FIM_ARQUIVO,',
        ])
        for fonte, fim in [('', '1,1,FIM_ARQUIVO,'), ('x', '1,2,FIM_ARQUIVO,'),
                           ('\n\n', '3,1,FIM_ARQUIVO,'), ('x\r ', '1,4,FIM_ARQUIVO,')]:
            with self.subTest(fonte=fonte):
                self.assertEqual(str(lexico.analisar(fonte)[-1]), fim)

    def test_comentario_nao_aninha_e_texto_preserva_lexema(self):
        self.assertEqual([t.lexema for t in lexico.analisar('/* /* */x')], ['x', ''])
        texto = r'"ação // /* */\n\t\"\\"'
        tokens = lexico.analisar(texto + ' 007 0.125')
        self.assertEqual([(t.tipo, t.lexema) for t in tokens[:-1]], [
            ('TEXTO', texto), ('INTEIRO', '007'), ('REAL', '0.125'),
        ])

    def test_erros_lexicos_ancorados(self):
        casos = [('3.', 1, 2), ('.5', 1, 1), ('1.2.3', 1, 4),
                 ('\n  /* aberto', 2, 3), ('"ab', 1, 1), ('"a\nb"', 1, 1),
                 ('"a\rb"', 1, 1), ('"abc\\', 1, 1),
                 (r'"a\q"', 1, 3), (r'"\u1234"', 1, 2),
                 ('!', 1, 1), ('x @', 1, 3), ('ação', 1, 2),
                 ('١', 1, 1), ('x\u00a0y', 1, 2), ('\ufeffx', 1, 1)]
        for fonte, linha, coluna in casos:
            with self.subTest(fonte=fonte):
                with self.assertRaises(ErroMPL) as cm:
                    lexico.analisar(fonte)
                self.assertEqual((cm.exception.fase, cm.exception.linha, cm.exception.coluna),
                                 ('lexico', linha, coluna))


class SintaticoTest(unittest.TestCase):
    def test_precedencia_completa(self):
        self.assertEqual(forma(expressao('a ou b e c == d < x + y * -nao f(2)')), (
            'binario ou', [('variavel a', []), ('binario e', [
                ('variavel b', []), ('binario ==', [('variavel c', []),
                    ('binario <', [('variavel d', []), ('binario +', [
                        ('variavel x', []), ('binario *', [('variavel y', []),
                            ('unario -', [('unario nao', [('chamada f', [
                                ('literal inteiro 2', [])])])])])])])])])]))

    def test_binarios_associativos_a_esquerda(self):
        for op in ['ou', 'e', '==', '!=', '<', '<=', '>', '>=', '+', '-', '*', '/', '%']:
            with self.subTest(op=op):
                self.assertEqual(forma(expressao('a ' + op + ' b ' + op + ' c')), (
                    'binario ' + op, [('binario ' + op, [('variavel a', []),
                                                       ('variavel b', [])]), ('variavel c', [])]))

    def test_parenteses_e_unarios(self):
        self.assertEqual(forma(expressao('-(1 + 2) * --3')), ('binario *', [
            ('unario -', [('binario +', [('literal inteiro 1', []), ('literal inteiro 2', [])])]),
            ('unario -', [('unario -', [('literal inteiro 3', [])])]),
        ]))

    def test_literais_decodificados_e_formatados(self):
        casos = [('0007', 'inteiro', 7, 'literal inteiro 7'),
                 ('01.23456789', 'real', 1.23456789, 'literal real 1.234568'),
                 ('verdadeiro', 'logico', True, 'literal logico verdadeiro'),
                 ('falso', 'logico', False, 'literal logico falso'),
                 (r'"ação\n\t\"\\"', 'texto', 'ação\n\t"\\', r'literal texto "ação\n\t\"\\"')]
        for fonte, tipo, valor, rotulo in casos:
            with self.subTest(fonte=fonte):
                no = expressao(fonte)
                self.assertEqual(no.rotulo, rotulo)
                self.assertEqual(no.extra, {'kind': 'literal', 'tipo': tipo, 'valor': valor})
                self.assertIs(type(no.extra['valor']), type(valor))

    def test_comandos_e_estrutura_dos_extras(self):
        raiz = analisar('''funcao real soma(inteiro a, real b, texto c, logico d) {
  inteiro x;
  real y = a + b;
  texto z = c;
  logico w = d;
  x = 1;
  se (w) { escreva(z); } senao { soma(x, y, z, w); }
  enquanto (w) { { w = falso; } }
  retorne y;
}
funcao vazio principal() { soma(1, 2.0, "ok", verdadeiro); retorne; }
''')
        funcao, principal = raiz.filhos
        self.assertEqual(funcao.extra, {'kind': 'funcao', 'nome': 'soma', 'tipo': 'real'})
        parametros, bloco = funcao.filhos
        self.assertEqual(parametros.rotulo, 'parametros')
        self.assertEqual([p.extra for p in parametros.filhos], [
            {'kind': 'parametro', 'nome': 'a', 'tipo': 'inteiro'},
            {'kind': 'parametro', 'nome': 'b', 'tipo': 'real'},
            {'kind': 'parametro', 'nome': 'c', 'tipo': 'texto'},
            {'kind': 'parametro', 'nome': 'd', 'tipo': 'logico'},
        ])
        self.assertEqual([n.rotulo for n in bloco.filhos], [
            'declaracao x inteiro', 'declaracao y real', 'declaracao z texto',
            'declaracao w logico', 'atribuicao x', 'se', 'enquanto', 'retorne',
        ])
        self.assertEqual(bloco.filhos[0].filhos, [])
        self.assertEqual(len(bloco.filhos[5].filhos), 3)
        self.assertEqual(len(bloco.filhos[5].filhos[2].filhos[0].filhos), 4)
        self.assertEqual(principal.filhos[0].filhos, [])
        self.assertEqual(principal.filhos[1].filhos[1].filhos, [])
        pendentes = [raiz]
        while pendentes:
            no = pendentes.pop()
            kind = no.rotulo.split()[0]
            self.assertEqual(no.extra['kind'], kind)
            self.assertGreaterEqual(no.linha, 1)
            self.assertGreaterEqual(no.coluna, 1)
            if kind in {'funcao', 'parametro', 'declaracao', 'atribuicao', 'chamada', 'variavel'}:
                self.assertEqual(no.extra['nome'], no.rotulo.split()[1])
            if kind in {'binario', 'unario'}:
                self.assertEqual(no.extra['op'], no.rotulo.split()[1])
            pendentes.extend(no.filhos)

    def test_posicoes_dos_nos(self):
        raiz = analisar('\nfuncao inteiro f(inteiro a) {\n  inteiro x = -a + 2;\n  retorne g(x);\n}')
        registros = []
        def visitar(no):
            registros.append((no.rotulo, no.linha, no.coluna))
            for filho in no.filhos:
                visitar(filho)
        visitar(raiz)
        self.assertEqual(registros, [
            ('programa', 2, 1), ('funcao f inteiro', 2, 1), ('parametros', 2, 17),
            ('parametro a inteiro', 2, 18), ('bloco', 2, 29),
            ('declaracao x inteiro', 3, 3), ('binario +', 3, 18),
            ('unario -', 3, 15), ('variavel a', 3, 16), ('literal inteiro 2', 3, 20),
            ('retorne', 4, 3), ('chamada g', 4, 11), ('variavel x', 4, 13),
        ])

    def test_erro_no_token_encontrado(self):
        casos = [('funcao f() {}', 1, 8), ('inteiro x;', 1, 1),
                 ('funcao vazio f() {\n inteiro x = 1\n retorne;\n}', 3, 2),
                 ('funcao vazio f() {\n', 2, 1),
                 ('funcao vazio f(inteiro a,) {}', 1, 26),
                 ('funcao vazio f(vazio a) {}', 1, 16)]
        for fonte, linha, coluna in casos:
            with self.subTest(fonte=fonte):
                with self.assertRaises(ErroMPL) as cm:
                    analisar(fonte)
                self.assertEqual((cm.exception.fase, cm.exception.linha, cm.exception.coluna),
                                 ('sintatico', linha, coluna))

    def test_rejeita_comandos_e_expressoes_fora_da_gramatica(self):
        for comando in [';', '1 + 2;', 'x;', 'f() + 1;', 'escreva();', 'escreva(1, 2);',
                        'f(1,);', 'x = ;', 'x = y = 1;', 'vazio x;', 'inteiro se;',
                        'se (verdadeiro) retorne;', 'se (verdadeiro) {} senao retorne;',
                        'enquanto (verdadeiro) retorne;', 'escreva(+1);',
                        'escreva((1);', 'escreva(f()(1));', 'funcao vazio g() {}']:
            with self.subTest(comando=comando):
                with self.assertRaises(ErroMPL) as cm:
                    analisar('funcao vazio f() { ' + comando + ' }')
                self.assertEqual(cm.exception.fase, 'sintatico')

    def test_parser_nao_executa_semantica(self):
        raiz = analisar('funcao inteiro f() { se (1) {} retorne desconhecida(); } '
                        'funcao vazio f() { retorne 2; }')
        self.assertEqual(len(raiz.filhos), 2)
        self.assertEqual(len(raiz.filhos[0].filhos[1].filhos[0].filhos), 2)
        self.assertEqual(forma(analisar('')), ('programa', []))


if __name__ == '__main__':
    unittest.main()
