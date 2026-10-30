// Rede: os aparelhos na rede de casa (só ver; nada aqui mexe no roteador) e o nome que o dono dá a cada um.
import { $, abrirJanela, atualizar, cartao, consultar, data, falha, h, item, itens, modulo, mudar, plural, semAcao, vazio } from "../comum.js";
import { relativo } from "./aprovacoes.js";

const PAPEIS = { roteador: "roteador", servidor: "este servidor", pc: "o PC" };

// quem o aparelho é, do mais certo ao mais vago: o nome do dono, o que ele diz, o fabricante
const nomeDe = (a) => a.nome ?? a.nome_rede ?? a.fabricante ?? "Aparelho sem nome";

// "há 5 min" no mesmo dia; depois disso, a data
const vistoEm = (s) => (Date.now() / 1000 - s < 86400 ? relativo(s) : `em ${data(s * 1000)}`);

// as partes do detalhe, separadas por " · " (o MAC vai em letra de máquina)
function detalhe(a) {
  const partes = [a.ip, h("code", null, a.mac),
    a.nome && a.nome_rede !== a.nome && a.nome_rede,
    (a.nome || a.nome_rede) && a.fabricante,
    a.mac_privado && "MAC privado",
    !a.conectado && a.ultimo && `visto ${vistoEm(a.ultimo)}`].filter(Boolean);
  return partes.flatMap((p, i) => (i ? [" · ", p] : [p]));
}

function itemAparelho(a) {
  return item({
    led: a.conectado ? "ok" : "fora", chave: `aparelho:${a.mac}`,
    nome: [h("strong", null, nomeDe(a)),
      PAPEIS[a.papel] && PAPEIS[a.papel] !== nomeDe(a).toLowerCase() && h("span", { class: "selo" }, PAPEIS[a.papel]),
      a.novo && h("span", { class: "selo neutro" }, "novo na rede")],
    detalhe: detalhe(a),
    acoes: h("button", { type: "button", class: "discreto", onclick: () => janelaNomear(a) }, a.nome ? "Renomear" : "Nomear"),
  });
}

function janelaNomear(a) {
  const nome = h("input", { name: "nome", maxlength: 40, autocomplete: "off", value: a.nome ?? "",
    placeholder: a.nome_rede ?? "ex.: TV da sala" });
  const gravar = async (valor) => {
    $("#janela").close();
    if (await mudar("rede.nomear", { mac: a.mac, nome: valor })) atualizar();
  };
  abrirJanela(a.nome || a.nome_rede || a.fabricante ? `Nomear ${nomeDe(a)}` : "Nomear o aparelho",
    h("p", { class: "fraco" }, [a.ip, a.mac, a.fabricante, a.mac_privado && "MAC privado"].filter(Boolean).join(" · ")),
    h("p", { class: "fraco" }, "O nome fica só aqui no painel (e a Atena o usa); o aparelho e o roteador não mudam."),
    h("form", { class: "resposta", onsubmit: (evento) => {
      evento.preventDefault();
      gravar(nome.value.trim());
    } }, nome, h("button", { type: "submit", class: "principal" }, "Gravar"),
    a.nome && h("button", { type: "button", class: "discreto", onclick: () => gravar("") }, "Tirar o nome")));
  nome.focus();
}

export async function telaRede() {
  const r = await consultar("rede.aparelhos");
  if (r.ok === false) return [cartao("Rede de casa", falha(r), semAcao(r, "rede.aparelhos"))];
  const { aparelhos, conectados, rede, varrido_em, varrendo } = r.resultado;
  const agora = aparelhos.filter((a) => a.conectado);
  const antes = aparelhos.filter((a) => !a.conectado);
  const procurar = h("button", { type: "button", class: "discreto", onclick: async (evento) => {
    const botao = evento.currentTarget;
    botao.disabled = true;
    botao.textContent = "Procurando…";
    const x = await consultar("rede.aparelhos", { agora: true });
    if (x.ok === false) {
      botao.replaceWith(falha(x));
      return;
    }
    atualizar();
  } }, "Procurar agora");
  return [
    modulo("Na rede agora", plural(conectados, "aparelho", "aparelhos"),
      itens(agora.map(itemAparelho)),
      h("p", { class: "fraco" }, `${rede} · ${varrendo ? "procurando de novo…" : `procurado ${relativo(varrido_em)}`}`),
      h("div", { class: "botoes" }, procurar)),
    modulo("Já vistos", antes.length ? plural(antes.length, "aparelho", "aparelhos") : null,
      itens(antes.map(itemAparelho), vazio("Ninguém mais passou pela rede desde que o painel começou a olhar.", "andorinha"), null, "rede"),
      h("p", { class: "fraco" }, "O servidor pergunta a cada endereço da rede quem está ali, e só olha: não bloqueia nem mexe "
        + "no roteador. Celular costuma usar um MAC privado em cada rede, sem fabricante: o nome que você der é o que "
        + "o identifica. Sem nome e sumido há 30 dias, o aparelho sai da lista.")),
  ];
}
