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
- `update-prices.py` — consulta a API da Nintendo em lotes de 5 e reescreve o
  `data.json` e o bloco JSON do `index.html`. Imprime `MUDOU=1` ou `MUDOU=0`
  na última linha; a Action lê isso para escolher a mensagem do commit.
- `notify-telegram.py` — manda o alerta pelo bot. `--resumo` para o panorama do
  dia, `--novidades anterior.json` para avisar só quando entra promoção ou o
  preço cai, `--simular` para ver a mensagem sem enviar. Sem os secrets, avisa
  e sai com código 0 — a Action não quebra por falta deles.
- `telegram-chat-id.py` — roda uma vez, na máquina do dono, para descobrir o
  `chat_id`. Lê o token de `TELEGRAM_TOKEN` e não imprime o token.
- `.github/workflows/update-prices.yml` — roda 05, 11, 17 e 23 UTC (02, 08, 14
  e 20 em Brasília). Atualiza, commita, avisa promoção nova em toda rodada e
  manda o resumo do dia só na rodada das 17 UTC.

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

**Amazon / mídia física** — sem automação. O campo `phys` é checagem manual, e
`physChecked` diz de quando. Scraping da Amazon a partir do runner do GitHub
tende a apanhar CAPTCHA (IP de datacenter) e, pior, a devolver preço de outro
vendedor ou de outra edição — erro silencioso. Fora dos termos de uso deles.

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
2. ~~Publicar como site estático.~~ Feito em 01/09/2026: repositório público
   `brugo/eshop-busca`, no ar em https://brugo.github.io/eshop-busca/.
3. ~~Automatizar a atualização.~~ Feito em 01/09/2026 pela Action. A tarefa
   agendada antiga na conta Claude do dono ficou redundante — desligar.
4. O alerta diário virou Telegram, não e-mail: dispensa SMTP e senha de app, e
   contorna o bloqueio de imagens externas do Gmail dele. Falta o dono criar o
   bot no `@BotFather` e gravar `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` como
   secrets — credencial não passa por sessão de assistente.
5. Próxima ideia: ler o grupo de ofertas de Nintendo do Telegram para alimentar
   os preços de mídia física, que hoje são checagem manual. O bot precisa estar
   no grupo com o privacy mode desligado; `getUpdates` só guarda ~24h e não lê
   histórico anterior à entrada dele. Começar casando o texto com os títulos da
   lista por código puro, sem modelo.

## Preferências

- Responder em português.
- Nada de emoji.
- A página tem identidade própria (Archivo + IBM Plex Sans/Mono, acento ciano,
  vermelho só para promoção). Manter, não trocar por tema genérico.
