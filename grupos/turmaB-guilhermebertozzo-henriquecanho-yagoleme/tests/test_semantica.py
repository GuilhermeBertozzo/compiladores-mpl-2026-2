"""Casos adicionais de tipos e escopos, independentes do corpus oficial."""
import unittest

from mplc import lexico, sintatico, semantica
from mplc.erros import ErroMPL


def analisar(fonte):
    arvore = sintatico.analisar(lexico.analisar(fonte))
    return arvore, semantica.analisar(arvore)


class SemanticaTests(unittest.TestCase):
    def recusa(self, fonte, linha=None):
        with self.assertRaises(ErroMPL) as contexto:
            analisar(fonte)
        self.assertEqual(contexto.exception.fase, 'semantico')
        if linha is not None:
            self.assertEqual(contexto.exception.linha, linha)

    def test_retorno_caminhos(self):
        analisar('funcao inteiro f(logico b) { se(b){retorne 1;} senao{retorne 2;} } funcao vazio principal(){}')
        self.recusa('funcao inteiro f(){ enquanto(verdadeiro){retorne 1;} } funcao vazio principal(){}')
        self.recusa('funcao inteiro f(){se(verdadeiro){retorne 1;}} funcao vazio principal(){}', 1)

    def test_confere_inalcancavel(self):
        self.recusa('funcao inteiro f(){retorne 1; escreva(x);} funcao vazio principal(){}')

    def test_retornos(self):
        self.recusa('funcao inteiro f(){retorne;} funcao vazio principal(){}')
        self.recusa('funcao real f(){retorne falso;} funcao vazio principal(){}')
        analisar('funcao real f(){retorne 2;} funcao vazio principal(){real x=f();}')

    def test_assinaturas(self):
        self.recusa('funcao vazio principal(){} funcao vazio principal(){}')
        self.recusa('funcao inteiro principal(){retorne 1;}')
        self.recusa('funcao vazio f(inteiro x, inteiro x){} funcao vazio principal(){}')
        self.recusa('funcao vazio f(inteiro x){} funcao vazio principal(){f(1.5);}')
        analisar('funcao vazio principal(){f(1);} funcao vazio f(real x){}')

    def test_vazio_em_expressao(self):
        for uso in ('escreva(f());', 'logico x=f()==f();', 'f(f());'):
            with self.subTest(uso=uso):
                self.recusa('funcao vazio f(){} funcao vazio principal(){'+uso+'}')

    def test_escopos_sombreamento(self):
        arvore, tabela = analisar(
            'funcao inteiro f(inteiro n){inteiro n=2; {inteiro n=3; escreva(n);} retorne n;} funcao vazio principal(){}')
        self.assertEqual([e.numero for e in tabela], list(range(6)))
        slots = [s.slot for e in tabela for s in e.simbolos.values() if s.categoria != 'funcao']
        self.assertEqual(len(slots), len(set(slots)))
        self.recusa('funcao vazio principal(){{inteiro x=1;} escreva(x);}')
        self.recusa('funcao vazio principal(){x=1; inteiro x;}')
        self.recusa('funcao vazio principal(){inteiro x; inteiro x;}')

    def test_matriz_tipos(self):
        aceitas = ('1+2.5', '"a"+"b"', '1==1.0', 'verdadeiro!=falso', '"a"=="b"', '-1.5', 'nao falso')
        recusadas = ('verdadeiro+1', '"a"<"b"', '1 e verdadeiro', 'nao 1', '1%2.5', '"a"==1', '-"a"')
        for expr in aceitas:
            with self.subTest(expr=expr):
                analisar('funcao vazio principal(){escreva('+expr+');}')
        for expr in recusadas:
            with self.subTest(expr=expr):
                self.recusa('funcao vazio principal(){escreva('+expr+');}')


if __name__ == '__main__':
    unittest.main()
