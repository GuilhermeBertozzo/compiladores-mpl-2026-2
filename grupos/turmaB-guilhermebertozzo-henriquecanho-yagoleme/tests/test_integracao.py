"""Programas independentes do corpus, passando pelo compilador e pela VM.

Rodar: python3 -m unittest discover -s tests -p test_integracao.py -v
As saidas esperadas sao calculadas manualmente. Ordem esquerda-direita e
inicializador que le o nome externo seguem os casos pedidos na revisao;
a especificacao nao detalha explicitamente essas duas convencoes.
"""
from io import StringIO
from pathlib import Path
import os
import subprocess
import tempfile
from textwrap import dedent
import unittest

from mplc.erros import ErroMPL
from mplc.principal import compilar_ate
from mplc import vm


RAIZ = Path(__file__).resolve().parents[1]


def fonte(texto):
    return dedent(texto).strip() + '\n'


class IntegracaoTests(unittest.TestCase):
    def executar(self, programa):
        bytecode = '\n'.join(compilar_ate(fonte(programa), 'bytecode')) + '\n'
        saida = StringIO()
        vm.executar(bytecode, saida)
        return saida.getvalue()

    def test_valores_padrao_reinicializados_em_cada_iteracao(self):
        # Detecta slots locais que conservam o valor da iteracao anterior.
        self.assertEqual(self.executar('''
            funcao vazio principal() {
              inteiro i = 0;
              enquanto (i < 3) {
                inteiro n;
                real r;
                logico b;
                texto t;
                escreva(n);
                escreva(r);
                escreva(b);
                escreva("[" + t + "]");
                n = 99;
                r = 2.5;
                b = verdadeiro;
                t = "alterado";
                i = i + 1;
              }
            }
        '''), '0\n0.000000\nfalso\n[]\n' * 3)

    def test_inicializador_le_externo_e_sombra_tem_outro_tipo(self):
        self.assertEqual(self.executar('''
            funcao real amplia(inteiro x) {
              real x = x + 0.5;
              { real x = x + 1; escreva(x); }
              retorne x;
            }
            funcao vazio principal() {
              inteiro x = 7;
              { real x = x + 0.25; escreva(x); }
              escreva(x);
              escreva(amplia(x));
              escreva(x);
            }
        '''), '7.250000\n7\n8.500000\n7.500000\n7\n')

    def test_sombras_em_blocos_irmaos_e_reentrada_no_loop(self):
        self.assertEqual(self.executar('''
            funcao vazio principal() {
              inteiro x = 10;
              inteiro i;
              enquanto (i < 3) {
                inteiro x = x + i;
                escreva(x);
                x = 99;
                i = i + 1;
              }
              { texto x = "irmao"; escreva(x); }
              { logico x; escreva(x); }
              escreva(x);
            }
        '''), '10\n11\n12\nirmao\nfalso\n10\n')

    def test_quatro_tipos_de_argumentos_passados_por_valor(self):
        self.assertEqual(self.executar('''
            funcao vazio muda(inteiro n, real r, logico b, texto t) {
              n = n + 1;
              r = r + 0.5;
              b = nao b;
              t = t + "!";
              escreva(n); escreva(r); escreva(b); escreva(t);
            }
            funcao vazio principal() {
              inteiro n = 4;
              real r = 1.25;
              logico b = falso;
              texto t = "oi";
              muda(n, r, b, t);
              escreva(n); escreva(r); escreva(b); escreva(t);
            }
        '''), '5\n1.750000\nverdadeiro\noi!\n4\n1.250000\nfalso\noi\n')

    def test_argumentos_repetidos_nao_compartilham_variavel(self):
        self.assertEqual(self.executar('''
            funcao inteiro muda(inteiro a, inteiro b) {
              a = 8;
              escreva(b);
              b = 9;
              retorne a;
            }
            funcao vazio principal() {
              inteiro x = 3;
              escreva(muda(x, x));
              escreva(x);
            }
        '''), '3\n8\n3\n')

    def test_argumentos_e_operandos_avaliados_esquerda_direita(self):
        # Efeitos observaveis distinguem ordem de avaliacao de associatividade.
        self.assertEqual(self.executar('''
            funcao inteiro marca(inteiro x) { escreva(x); retorne x; }
            funcao inteiro par(inteiro a, inteiro b) {
              escreva(90);
              retorne a * 10 + b;
            }
            funcao vazio principal() {
              escreva(par(marca(1), marca(2) + marca(3)));
              escreva(marca(4) - marca(5) * marca(6));
              escreva(par(par(marca(7), marca(8)), marca(9)));
            }
        '''), '1\n2\n3\n90\n15\n4\n5\n6\n-26\n7\n8\n90\n9\n90\n789\n')

    def test_logicos_avaliam_ambos_os_lados_inclusive_chamadas(self):
        self.assertEqual(self.executar('''
            funcao logico marca(inteiro id, logico b) { escreva(id); retorne b; }
            funcao vazio principal() {
              escreva(marca(1, falso) e marca(2, verdadeiro));
              escreva(marca(3, verdadeiro) ou marca(4, falso));
            }
        '''), '1\n2\nfalso\n3\n4\nverdadeiro\n')

    def test_recursao_mutua_preserva_locais_e_valores_pendentes(self):
        # principal vem antes das duas assinaturas; retornos usam locais apos CALL.
        self.assertEqual(self.executar('''
            funcao vazio principal() { escreva(a(4)); escreva(b(3)); }
            funcao inteiro a(inteiro n) {
              inteiro salvo = n;
              se (n == 0) { retorne 1; }
              inteiro resposta = b(n - 1);
              retorne salvo + resposta;
            }
            funcao inteiro b(inteiro n) {
              inteiro salvo = n * 10;
              se (n == 0) { retorne 2; }
              inteiro resposta = a(n - 1);
              retorne salvo + resposta;
            }
        '''), '47\n43\n')

    def test_recursao_duas_chamadas_na_mesma_expressao(self):
        self.assertEqual(self.executar('''
            funcao inteiro arvore(inteiro n) {
              se (n == 0) { retorne 1; }
              retorne arvore(n - 1) + arvore(n - 1);
            }
            funcao vazio principal() { escreva(arvore(6)); }
        '''), '64\n')

    def test_conversao_inteiro_real_declaracao_atribuicao_argumento_retorno(self):
        self.assertEqual(self.executar('''
            funcao real metade(real x) { retorne x / 2; }
            funcao real devolve(inteiro x) { retorne x; }
            funcao real quociente() { retorne 7 / 2; }
            funcao vazio principal() {
              real x = 3;
              escreva(x);
              x = 5;
              escreva(x);
              escreva(metade(7));
              escreva(devolve(9));
              escreva(quociente());
              x = 7 / 2;
              escreva(x);
              escreva(metade(7 / 2));
            }
        '''), '3.000000\n5.000000\n3.500000\n9.000000\n3.000000\n3.000000\n1.500000\n')

    def test_conversao_nos_dois_lados_de_operacoes(self):
        casos = [
            ('2 + 0.5', '2.500000'), ('0.5 + 2', '2.500000'),
            ('2 - 0.5', '1.500000'), ('0.5 - 2', '-1.500000'),
            ('2 * 0.5', '1.000000'), ('0.5 * 2', '1.000000'),
            ('5 / 2.0', '2.500000'), ('5.0 / 2', '2.500000'),
            ('2 == 2.0', 'verdadeiro'), ('2.0 == 2', 'verdadeiro'),
            ('2 != 2.0', 'falso'), ('2.0 != 2', 'falso'),
            ('2 < 2.5', 'verdadeiro'), ('2.5 < 2', 'falso'),
            ('2 <= 2.0', 'verdadeiro'), ('2.0 <= 2', 'verdadeiro'),
            ('2 > 2.5', 'falso'), ('2.5 > 2', 'verdadeiro'),
            ('2 >= 2.0', 'verdadeiro'), ('2.0 >= 2', 'verdadeiro'),
        ]
        for expr, esperado in casos:
            with self.subTest(expressao=expr):
                self.assertEqual(self.executar(
                    'funcao vazio principal() { escreva(' + expr + '); }'), esperado + '\n')

    def test_recusa_conversoes_nao_permitidas_antes_da_execucao(self):
        casos = [
            'inteiro x = 2.0;', 'inteiro x; x = 2.0;',
            'recebe(2.0);', 'inteiro x = verdadeiro;', 'real x = falso;',
            'logico x = 1;', 'texto x = 2;', 'texto x = "a" + 2;',
            'escreva(1.0 % 2);', 'escreva(1 % 2.0);',
            'escreva("a" < "b");', 'escreva(verdadeiro == 1);',
        ]
        for comando in casos:
            with self.subTest(comando=comando):
                with self.assertRaises(ErroMPL) as cm:
                    compilar_ate('funcao vazio recebe(inteiro x) {}\n'
                                 'funcao vazio principal() {\n' + comando + '\n}', 'bytecode')
                self.assertEqual((cm.exception.fase, cm.exception.linha), ('semantico', 3))
        with self.assertRaises(ErroMPL) as cm:
            compilar_ate('funcao inteiro f() {\nretorne 2.0;\n}\n'
                         'funcao vazio principal() {}', 'bytecode')
        self.assertEqual((cm.exception.fase, cm.exception.linha), ('semantico', 2))

    def test_recusa_vazio_em_todos_os_contextos_de_expressao(self):
        for comando in ['escreva(nada());', 'inteiro x = nada();',
                        'recebe(nada());', 'escreva(nada() == nada());']:
            with self.subTest(comando=comando):
                with self.assertRaises(ErroMPL) as cm:
                    compilar_ate('funcao vazio nada() {}\n'
                                 'funcao vazio recebe(inteiro x) {}\n'
                                 'funcao vazio principal() {\n' + comando + '\n}', 'bytecode')
                self.assertEqual((cm.exception.fase, cm.exception.linha), ('semantico', 4))

    def test_retorno_em_blocos_aninhados_e_fallback_apos_loop(self):
        self.assertEqual(self.executar('''
            funcao inteiro escolhe(inteiro n) {
              enquanto (n > 0) {
                se (n == 2) { { retorne 20; } }
                n = n - 1;
              }
              se (n == 0) { retorne 0; } senao { retorne -1; }
            }
            funcao vazio principal() {
              escreva(escolhe(3)); escreva(escolhe(0)); escreva(escolhe(-2));
            }
        '''), '20\n0\n-1\n')

    def test_loop_literal_nao_dispensa_retorno_estrutural(self):
        # E3: analise estrutural sem avaliar condicoes. Conforme a politica
        # conservadora documentada no README, o laco exige retorno posterior.
        with self.assertRaises(ErroMPL) as cm:
            compilar_ate(fonte('''
                funcao inteiro sempre() {
                  enquanto (verdadeiro) {
                    retorne 17;
                  }
                }
                funcao vazio principal() { escreva(sempre()); }
            '''), 'bytecode')
        self.assertEqual((cm.exception.fase, cm.exception.linha), ('semantico', 1))

    def test_loop_condicional_nao_garante_retorno(self):
        with self.assertRaises(ErroMPL) as cm:
            compilar_ate(fonte('''
                funcao inteiro talvez(logico b) {
                  enquanto (b) { retorne 17; }
                }
                funcao vazio principal() { escreva(talvez(falso)); }
            '''), 'bytecode')
        self.assertEqual((cm.exception.fase, cm.exception.linha), ('semantico', 1))

    def test_divisao_e_resto_truncam_em_direcao_a_zero(self):
        self.assertEqual(self.executar('''
            funcao vazio principal() {
              escreva(-7 / 2); escreva(7 / -2); escreva(-7 / -2);
              escreva(-7 % 2); escreva(7 % -2); escreva(-7 % -2);
              escreva(7 / 2 + 0.5); escreva(-7 / 2.0);
            }
        '''), '-3\n-3\n3\n-1\n1\n-1\n3.500000\n-3.500000\n')

    def test_texto_unicode_e_escapes_atraves_do_bytecode(self):
        self.assertEqual(self.executar(r'''
            funcao texto eco(texto t) { retorne t + "!"; }
            funcao vazio principal() {
              escreva(eco("ação\n\t\"\\"));
              escreva("a" + "b" == "ab");
              escreva("á" != "a");
            }
        '''), 'ação\n\t"\\!\nverdadeiro\nverdadeiro\n')

    def test_erro_execucao_aponta_comando_da_funcao_chamada(self):
        for expr in ['7 / 0', '7 % 0', '7.0 / 0']:
            with self.subTest(expressao=expr):
                programa = ('funcao inteiro falha() {\n  escreva(' + expr + ');\n'
                            '  retorne 0;\n}\n'
                            'funcao vazio principal() { escreva(falha()); }\n')
                # Divisao por zero e erro de execucao, mesmo com operandos constantes.
                bytecode = '\n'.join(compilar_ate(programa, 'bytecode')) + '\n'
                with self.assertRaises(ErroMPL) as cm:
                    vm.executar(bytecode, StringIO())
                self.assertEqual((cm.exception.fase, cm.exception.linha), ('execucao', 2))

    def test_sem_curto_circuito_preserva_erro_no_lado_direito(self):
        for expr in ['falso e (1 / 0 == 0)', 'verdadeiro ou (1 % 0 == 0)']:
            with self.subTest(expressao=expr):
                bytecode = '\n'.join(compilar_ate(
                    'funcao vazio principal() {\n  escreva(' + expr + ');\n}', 'bytecode'))
                with self.assertRaises(ErroMPL) as cm:
                    vm.executar(bytecode, StringIO())
                self.assertEqual((cm.exception.fase, cm.exception.linha), ('execucao', 2))

    def test_cli_dumps_nao_criam_nem_sobrescrevem_arquivos(self):
        ambiente = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        with tempfile.TemporaryDirectory(prefix='mpl-integracao-') as pasta:
            caminho = Path(pasta) / 'programa com espaço.mpl'
            caminho.write_text('funcao vazio principal() { escreva(42); }\n', encoding='utf-8')
            destino = caminho.with_suffix('.mplb')
            for preexistente in (False, True):
                if preexistente:
                    destino.write_bytes(b'artefato anterior\n')
                antes = {p.name: p.read_bytes() for p in Path(pasta).iterdir()}
                for modo in ['--tokens', '--ast', '--tabela', '--ir']:
                    with self.subTest(modo=modo, preexistente=preexistente):
                        resultado = subprocess.run([str(RAIZ / 'compilar'), modo, str(caminho)],
                                                   cwd=RAIZ, env=ambiente, capture_output=True,
                                                   text=True, encoding='utf-8', timeout=10)
                        self.assertEqual(resultado.returncode, 0, resultado.stderr)
                        self.assertEqual(resultado.stderr, '')
                        self.assertTrue(resultado.stdout.strip())
                        self.assertFalse(resultado.stdout.startswith('\ufeff'))
                        self.assertEqual({p.name: p.read_bytes() for p in Path(pasta).iterdir()}, antes)

    def test_dumps_param_na_fase_pedida(self):
        sintaxe_invalida = 'funcao vazio principal() { inteiro x = ; }'
        self.assertTrue(compilar_ate(sintaxe_invalida, 'tokens')[-1].endswith('FIM_ARQUIVO,'))
        with self.assertRaises(ErroMPL) as cm:
            compilar_ate(sintaxe_invalida, 'ast')
        self.assertEqual(cm.exception.fase, 'sintatico')
        semantica_invalida = 'funcao vazio principal() { escreva(inexistente); }'
        self.assertIn('        variavel inexistente', compilar_ate(semantica_invalida, 'ast'))
        with self.assertRaises(ErroMPL) as cm:
            compilar_ate(semantica_invalida, 'tabela')
        self.assertEqual(cm.exception.fase, 'semantico')
        self.assertTrue(compilar_ate('funcao vazio principal() { escreva(1 / 0); }', 'ir'))


if __name__ == '__main__':
    unittest.main()
