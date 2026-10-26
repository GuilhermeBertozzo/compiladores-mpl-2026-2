// Demonstração: transfere três discos e calcula o total de movimentos.
funcao inteiro quantidade(inteiro discos) {
  se (discos <= 0) {
    retorne 0;
  }
  retorne 2 * quantidade(discos - 1) + 1;
}

funcao vazio hanoi(inteiro discos, texto origem, texto destino, texto apoio) {
  se (discos > 0) {
    hanoi(discos - 1, origem, apoio, destino);
    escreva(origem + " -> " + destino);
    hanoi(discos - 1, apoio, destino, origem);
  }
}

funcao vazio principal() {
  escreva("Torre de Hanoi: 3 discos");
  hanoi(3, "A", "C", "B");
  inteiro passos;
  passos = 2 * 3 + 1;
  inteiro total = quantidade(3);
  escreva("Movimentos realizados:");
  escreva(total);
  escreva("Conferencia:");
  escreva(passos == total);
}
