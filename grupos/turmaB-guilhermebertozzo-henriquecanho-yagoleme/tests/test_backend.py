"""Regressoes do backend; executar com unittest discover -s tests.

O corpus original e somente lido. Bytecode e executado em memoria ou em
diretorios temporarios, sem criar artefatos nas fixtures.
"""
from dataclasses import replace
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mplc import gerador, intermediario, lexico, principal, semantica, sintatico, vm
from mplc.erros import ErroMPL
from verificar import conta_operadores


RAIZ = Path(__file__).resolve().parents[1]


def ir(fonte):
    arvore = sintatico.analisar(lexico.analisar(fonte))
    tabela = semantica.analisar(arvore)
    return intermediario.gerar(arvore, tabela)


def executar(fonte):
    saida = StringIO()
    vm.executar('\n'.join(gerador.gerar(ir(fonte))), saida)
    return saida.getvalue()


class BackendTests(unittest.TestCase):
    def test_corpus_positivo(self):
        for arquivo in sorted((RAIZ / 'testes/positivos').glob('*.mpl')):
            with self.subTest(programa=arquivo.name):
                self.assertEqual(executar(arquivo.read_text(encoding='utf-8')),
                                 arquivo.with_suffix('.saida').read_text(encoding='utf-8'))

    def test_corpus_erros_execucao(self):
        for arquivo in sorted((RAIZ / 'testes/negativos').glob('exec*.mpl')):
            with self.subTest(programa=arquivo.name):
                fase, linha, coluna = arquivo.with_suffix('.erro').read_text().strip().split('|')
                with self.assertRaises(ErroMPL) as erro:
                    executar(arquivo.read_text())
                self.assertEqual((erro.exception.fase, erro.exception.linha), (fase, int(linha)))

    def test_conversoes_no_consumo(self):
        self.assertEqual(executar('''
            funcao real retorna() { retorne 7 / 2; }
            funcao real recebe(real x) { retorne x; }
            funcao vazio principal() {
                real x = 7 / 2;
                escreva(x);
                x = -7 / 2;
                escreva(x);
                escreva(retorna());
                escreva(recebe(7 / 2));
                escreva(7 / 2 + 0.5);
                escreva(0.5 + 7 / 2);
                escreva(7 / 2 == 3.0);
                escreva(3.0 == 7 / 2);
                escreva(7 / 2 < 3.5);
            }
        '''), '3.000000\n-3.000000\n3.000000\n3.000000\n3.500000\n3.500000\nverdadeiro\nverdadeiro\nverdadeiro\n')

    def test_comparacao_mista_converte_filhos_mesmo_com_resultado_logico(self):
        # Python compara int/float sem promover int; MPL exige a conversao.
        self.assertEqual(executar('''
            funcao vazio principal() {
                escreva(9007199254740993 == 9007199254740992.0);
                escreva(9007199254740992.0 == 9007199254740993);
                escreva(9007199254740993 > 9007199254740992.0);
            }
        '''), 'verdadeiro\nverdadeiro\nfalso\n')

    def test_divisao_e_resto_sem_float_em_todos_os_sinais(self):
        grande = 10**200 + 7
        comandos, esperado = [], []
        for a in (7, -7, 0, grande, -grande):
            for b in (3, -3, grande, -grande):
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0):
                    q = -q
                comandos.extend((f'escreva(({a}) / ({b}));', f'escreva(({a}) % ({b}));'))
                esperado.extend((str(q), str(a - q * b)))
        fonte = 'funcao vazio principal() {' + '\n'.join(comandos) + '}'
        self.assertEqual(executar(fonte), '\n'.join(esperado) + '\n')

    def test_ambos_logicos_e_argumentos_em_ordem(self):
        self.assertEqual(executar('''
            funcao logico marca(inteiro n, logico valor) {
                escreva(n); retorne valor;
            }
            funcao inteiro numero(inteiro n) { escreva(n); retorne n; }
            funcao inteiro junta(inteiro a, inteiro b, inteiro c) {
                retorne a * 100 + b * 10 + c;
            }
            funcao vazio principal() {
                escreva(marca(1, falso) e marca(2, verdadeiro));
                escreva(marca(3, verdadeiro) ou marca(4, falso));
                escreva(junta(numero(5), numero(6), numero(7)));
                escreva(numero(8) - numero(9));
            }
        '''), '1\n2\nfalso\n3\n4\nverdadeiro\n5\n6\n7\n567\n8\n9\n-1\n')

    def test_logicos_nao_escondem_erro_no_lado_direito(self):
        for expr in ('falso e (1 / 0 == 0)', 'verdadeiro ou (1 % 0 == 0)'):
            with self.subTest(expr=expr), self.assertRaises(ErroMPL) as erro:
                executar(f'funcao vazio principal() {{\n  escreva({expr});\n}}')
            self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))

    def test_padroes_e_sombreamento_inicializador(self):
        self.assertEqual(executar('''
            funcao vazio principal() {
                inteiro a; real b; logico c; texto d;
                escreva(a); escreva(b); escreva(c); escreva(d);
                inteiro x = 8;
                { inteiro x = x + 1; escreva(x); }
                escreva(x);
                inteiro i = 0;
                enquanto (i < 3) {
                    inteiro z;
                    escreva(z);
                    z = 9;
                    i = i + 1;
                }
            }
        '''), '0\n0.000000\nfalso\n\n9\n8\n0\n0\n0\n')

    def test_parametros_por_valor_e_retorno_no_meio_de_laco(self):
        self.assertEqual(executar('''
            funcao inteiro muda(inteiro n) {
                n = n + 1;
                enquanto (verdadeiro) { retorne n; }
                retorne 0;
            }
            funcao vazio pare() { escreva(1); retorne; escreva(999); }
            funcao vazio principal() {
                inteiro n = 4;
                escreva(muda(n)); escreva(n);
                muda(50);
                pare();
                escreva(2);
            }
        '''), '5\n4\n1\n2\n')

    def test_recursao_profunda_nao_usa_pilha_python(self):
        profundidade = sys.getrecursionlimit() + 100
        self.assertLess(profundidade + 2, vm.MAX_QUADROS)
        self.assertEqual(executar(f'''
            funcao inteiro conta(inteiro n) {{
                se (n == 0) {{ retorne 0; }}
                inteiro salvo = n;
                retorne conta(n - 1) + salvo;
            }}
            funcao vazio principal() {{ escreva(conta({profundidade})); }}
        '''), f'{profundidade * (profundidade + 1) // 2}\n')

    def test_recursao_mutua_profunda(self):
        self.assertEqual(executar('''
            funcao logico par(inteiro n) {
                se (n == 0) { retorne verdadeiro; }
                retorne impar(n - 1);
            }
            funcao logico impar(inteiro n) {
                se (n == 0) { retorne falso; }
                retorne par(n - 1);
            }
            funcao vazio principal() { escreva(par(1500)); }
        '''), 'verdadeiro\n')

    def test_overflow_aponta_comando_da_chamada_multilinha(self):
        fonte = ('funcao inteiro f() {\n'
                 '  retorne\n'
                 '    f();\n'
                 '}\n'
                 'funcao vazio principal() { escreva(f()); }\n')
        with patch.object(vm, 'MAX_QUADROS', 8), self.assertRaises(ErroMPL) as erro:
            executar(fonte)
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))
        self.assertIn('estouro de pilha', str(erro.exception))

    def test_erros_multilinha_apontam_comandos(self):
        for comando in ('escreva(\n 1 / 0);', 'inteiro n =\n 1 % 0;',
                        'real n =\n 1.0 / 0.0;', 'se (\n 1 / 0 == 0) {}',
                        'enquanto (\n 1 / 0 == 0) {}'):
            with self.subTest(comando=comando), self.assertRaises(ErroMPL) as erro:
                executar('funcao vazio principal() {\n  ' + comando + '\n}')
            self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))

    def test_erro_em_funcao_aponta_comando_da_funcao(self):
        fonte = ('funcao inteiro f() {\n  retorne\n    7 / 0;\n}\n'
                 'funcao vazio principal() { escreva(f()); }')
        with self.assertRaises(ErroMPL) as erro:
            executar(fonte)
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (2, 3))

    def test_strings_preservam_escapes_unicode_e_separadores(self):
        valor = 'ação\u2028linha\u0085 fim'
        fonte = ('funcao vazio principal() { escreva("' + valor
                 + r'\n\t\"\\"); escreva("e ou nao + - / %" + "!"); }')
        self.assertEqual(executar(fonte), valor + '\n\t"\\\ne ou nao + - / %!\n')

    def test_ir_sem_expressoes_embutidas_e_com_destinos_existentes(self):
        fonte = '''
            funcao real soma(real a, real b, real c, real d) { retorne a+b+c+d; }
            funcao vazio principal() {
                real pequeno = 0.00000000000000000001;
                enquanto (pequeno > 0.0) {
                    se (verdadeiro) { pequeno = 0.0; } senao { escreva(1); }
                }
                escreva(soma(1, 2, 3, 4));
                escreva(1 + 2 * 3);
            }
        '''
        codigo = ir(fonte)
        linhas = intermediario.despejar(codigo)
        for linha in linhas:
            self.assertLessEqual(conta_operadores(linha), 1, linha)
        self.assertTrue(any(l.startswith('funcao soma ') for l in linhas))
        for funcao in codigo.funcoes:
            rotulos = {i.args[0] for i in funcao.instrucoes if i.op == 'label'}
            for i in funcao.instrucoes:
                if i.op in ('jfalse', 'jump'):
                    self.assertIn(i.args[-1], rotulos)
                if i.op == 'call':
                    self.assertIsInstance(i.args[1], int)
        self.assertEqual(executar(fonte), '10.000000\n7\n')

    def test_backend_consume_no_anotado_e_bytecode_depende_do_ir(self):
        No = sintatico.No
        literal = No('literal inteiro 7', linha=2, coluna=11, tipo='inteiro', valor=7)
        escreva = No('escreva', [literal], linha=2, coluna=3)
        arvore = No('programa', [No('funcao principal vazio',
            [No('parametros'), No('bloco', [escreva])], linha=1, coluna=1,
            nome='principal', tipo='vazio')])
        codigo = intermediario.gerar(arvore, [])
        arvore.filhos.clear()
        funcao = codigo.funcoes[0]
        funcao.instrucoes[0] = replace(funcao.instrucoes[0], args=(42,))
        bytecode = '\n'.join(gerador.gerar(codigo))
        saida = StringIO()
        with patch.object(sintatico, 'analisar', side_effect=AssertionError('AST proibida')):
            vm.executar(bytecode, saida)
        self.assertEqual(saida.getvalue(), '42\n')

    def test_bytecode_em_processo_separado_sem_fonte(self):
        bytecode = gerador.gerar(ir('funcao vazio principal() { escreva(42); }'))
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / 'programa.mplb'
            arquivo.write_text('\n'.join(bytecode) + '\n', encoding='utf-8')
            processo = subprocess.run([str(RAIZ / 'executar'), str(arquivo)],
                                      cwd=RAIZ, capture_output=True, text=True)
        self.assertEqual((processo.returncode, processo.stdout, processo.stderr), (0, '42\n', ''))

    def test_bytecode_crlf_e_execucoes_independentes(self):
        bytecode = '\r\n'.join(principal.compilar_ate(
            'funcao vazio principal() { escreva(42); }', 'bytecode')) + '\r\n'
        for _ in range(2):
            saida = StringIO()
            vm.executar(bytecode, saida)
            self.assertEqual(saida.getvalue(), '42\n')

    def test_bytecode_invalido_reporta_erros_controlados(self):
        for instrucao in ('JUMP ["ausente"]', 'CALL ["ausente", 0]', 'STORE ["x"]',
                          'LOAD ["ausente"]', 'PUSH [{}]', 'UNKNOWN []', 'RETURN [true]'):
            texto = 'MPLB 1\nFUNC ["principal", "vazio", []]\n7:3 ' + instrucao + '\nEND\n'
            with self.subTest(instrucao=instrucao), self.assertRaises(ErroMPL) as erro:
                vm.executar(texto, StringIO())
            self.assertEqual((erro.exception.fase, erro.exception.linha), ('execucao', 7))

    def test_limite_pilha_operandos(self):
        texto = ('MPLB 1\nFUNC ["principal", "vazio", []]\n'
                 '2:3 PUSH [1]\n3:3 PUSH [2]\n4:3 RETURN [false]\nEND\n')
        with patch.object(vm, 'MAX_OPERANDOS', 1), self.assertRaises(ErroMPL) as erro:
            vm.executar(texto, StringIO())
        self.assertEqual((erro.exception.linha, erro.exception.coluna), (3, 3))


if __name__ == '__main__':
    unittest.main()
