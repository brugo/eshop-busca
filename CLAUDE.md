# Radar da eShop

Rastreador de preços da wishlist de Nintendo Switch / Switch 2 do Humberto,
na eShop Brasil. Projeto nasceu numa sessão Cowork (nuvem)
e foi trazido para cá para resolver o que o sandbox de artifacts impedia.

## O que existe hoje

- `index.html` — página única, sem dependências. Todo o estado vive num bloco
  `<script type="application/json" id="tracker-data">` dentro do próprio HTML.
  O JS abaixo dele desenha a prateleira, os cards de promoção e a tabela.
- `data.json` — cópia solta do mesmo bloco de dados, para conveniência.
- `assets/<NSUID>.jpg` — as 24 capas, baixadas do CDN da Nintendo. A página usa
  sempre o arquivo local; o CDN ficou como reserva no atributo `data-cdn` de
  cada `<img>`, usado só se o arquivo local faltar.
- `fetch-covers.py` — rebaixa as capas a partir do `data.json`. Sem argumentos
  pula o que já existe; com `--force` refaz tudo. Rodar quando entrar jogo novo.

### Formato de cada jogo

| campo   | significado |
|---------|-------------|
| `n`     | nome |
| `id`    | NSUID (string) |
| `p`     | `SW` ou `SW2` |
| `s`     | slug da loja: `https://www.nintendo.com/pt-br/store/products/<s>/` |
| `img`   | caminho da capa oficial (ver abaixo) |
| `reg`   | preço cheio |
| `cur`   | preço com desconto (ausente quando não há oferta) |
| `pct`   | % de desconto (ausente quando não há oferta) |
| `ends`  | fim da oferta, ISO UTC (ausente quando não há oferta) |
| `low`   | menor preço eShop já registrado |
| `phys`  | melhor preço de mídia física conhecido (Amazon BR) |
| `hist`  | `[[data, preço], ...]`, uma entrada por dia |
| `note`  | só para títulos sem preço (Zelda: Ocarina of Time) |

No topo do JSON: `updated` (timestamp -03:00) e `physChecked` (data da última
checagem de preço físico).

## Fontes de dados

**Preços** — API oficial da Nintendo, sem chave:

    https://api.ec.nintendo.com/v1/price?country=BR&lang=pt&ids=ID1,ID2,...

`regular_price.raw_value` é o preço cheio. Se vier `discount_price`, use
`raw_value` como preço atual e `end_datetime` como fim da oferta.
`sales_status: "unreleased"` = sem preço ainda (caso do Ocarina of Time).
Na sessão da nuvem a API recusava lotes grandes; em grupos de 5 ou 6 funcionava.

**Capas** — arte oficial, servida pelo Cloudinary da Nintendo:

    https://assets.nintendo.com/image/upload/<transform>/store/software/<img>

O `img` de cada jogo já está no JSON. O transform em uso é `w_640/q_auto:best/f_jpg`.

A arte de origem é **16:9** (o CDN entrega no máximo 800x450 de útil), não é
quadrada nem tem a forma da caixa do jogo físico. Qualquer `c_fill` para um
formato mais alto come os logos pelas laterais — já aconteceu, e foi por isso
que os cards passaram de `aspect-ratio:105/170` para `16/9`. Não cortar.

## O problema que trouxe o projeto para cá

A página estava publicada como artifact no claude.ai. O visualizador de artifacts
roda num sandbox cujo CSP só permite recursos do próprio claude.ai, então
**toda imagem externa é bloqueada** — as capas nunca apareciam. As URLs estão
corretas (abrem normalmente no navegador); o bloqueio é do ambiente.

Por isso o `index.html` tem, para cada jogo, uma "caixa" desenhada em CSS
(gradiente com matiz fixa por título, faixa vermelha para Switch e azul para
Switch 2, inicial gigante ao fundo) e a `<img>` oficial por cima. Onde a imagem
carrega, ela ganha; onde é bloqueada, a caixa desenhada segura o layout.

**Resolvido em 01/09/2026**: as capas agora são arquivos locais em `assets/`, a
página não depende mais de domínio externo e as imagens aparecem. A caixa
desenhada continua como rede de segurança.

## Próximos passos pretendidos

1. ~~Baixar as 24 capas para `assets/` e referenciá-las localmente.~~ Feito em
   01/09/2026, junto com o `fetch-covers.py`.
2. Publicar como site estático (GitHub Pages, Vercel ou Netlify).
3. Automatizar a atualização diária — provavelmente uma GitHub Action que roda
   o fetch da API, reescreve o bloco JSON, faz commit e dispara o e-mail.
   Hoje isso é uma tarefa agendada na conta Claude do Humberto, que roda 17:00 UTC
   (14:00 em Brasília) e não tem acesso à máquina dele.
4. O e-mail diário vai para o endereço do dono, guardado no secret `ALERT_EMAIL`
   do repositório — o repositório é público, então o endereço não entra em arquivo
   nenhum. Atenção: no Gmail dele as imagens
   externas aparentemente estão bloqueadas por configuração ("perguntar antes de
   exibir imagens externas") — vale conferir antes de culpar o HTML.

## Preferências

- Responder em português.
- Nada de emoji.
- A página tem identidade própria (Archivo + IBM Plex Sans/Mono, acento ciano,
  vermelho só para promoção). Manter, não trocar por tema genérico.
