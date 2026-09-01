# -*- coding: utf-8 -*-
"""Le o canal publico de ofertas no Telegram e atualiza os precos de midia fisica.

Nao precisa de bot nem de token: canal publico tem uma versao web aberta em
t.me/s/<canal>. So enxerga o que esta na pagina (as ultimas ~20 mensagens),
entao roda junto com as quatro rodadas diarias de preco.

    python read-channel.py [--simular]

O texto do canal e escrito por terceiros: e dado, nunca instrucao. Daqui so
saem numero, nome da loja e link, e o titulo da mensagem fica gravado em
`physSrc` para a origem de cada preco ser audivel.
"""
import io
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone

CANAL = 'nintendobarato'
URL = 'https://t.me/s/%s' % CANAL
BRASILIA = timezone(timedelta(hours=-3))

# Palavras que nao distinguem um jogo de outro.
RUIDO = {
    'nintendo', 'switch', 'edition', 'edicao', 'ed', 'de', 'do', 'da', 'the',
    'a', 'o', 'e', 'para', 'jogo', 'midia', 'fisica', 'com', 'em', 'of', 'no',
    'na', 'lacrado', 'novo', 'br', 'nacional',
}
# Se um destes aparecer so de um lado, sao jogos diferentes (Chronicles 2 nao e
# Chronicles X; Remake nao e Rebirth).
DISTINTIVOS = {
    'zero', 'remake', 'remaster', 'remastered', 'reimagined', 'rebirth',
    'deluxe', 'definitive', 'collection', 'bundle', 'intergrade',
    'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii',
}


def modulo_precos():
    """Reaproveita o serializador do update-prices.py, para os dois scripts
    escreverem o data.json e o index.html exatamente no mesmo formato."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('update_prices', 'update-prices.py')
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def normaliza(texto):
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^0-9a-zA-Z]+', ' ', texto.lower())
    return texto.split()


def tokens(texto):
    limpo = ' '.join(normaliza(texto))
    # Tira o nome da plataforma antes de tudo: senao o "2" de "Switch 2" e lido
    # como parte do nome do jogo e "Dragon Quest VII (Switch 2)" deixa de casar
    # com "Dragon Quest VII".
    limpo = re.sub(r'\b(nintendo )?switch 2\b', ' ', limpo)
    limpo = re.sub(r'\bsw2\b', ' ', limpo)
    limpo = re.sub(r'\b(nintendo )?switch\b', ' ', limpo)
    return [t for t in limpo.split() if t not in RUIDO]


def marcadores(lista):
    return {t for t in lista if t in DISTINTIVOS or t.isdigit()}


def casa(titulo_jogo, titulo_msg):
    """Conservador de proposito: falso negativo custa uma oferta perdida,
    falso positivo poe preco de outro jogo no site."""
    cru_jogo = ' '.join(normaliza(titulo_jogo))
    cru_msg = ' '.join(normaliza(titulo_msg))
    # Titulo que existe nas duas geracoes: a oferta precisa dizer Switch 2,
    # senao e o cartucho de Switch 1, cujo update para Switch 2 e pago -- outro
    # produto, com outro preco.
    if 'switch 2 edition' in cru_jogo and 'switch 2' not in cru_msg:
        return False

    jogo = tokens(titulo_jogo)
    msg = tokens(titulo_msg)
    if not jogo or not msg:
        return False
    if not set(jogo).issubset(set(msg)):
        return False
    # Nenhum marcador pode existir so de um lado.
    return marcadores(jogo) == marcadores(msg)


def busca_mensagens():
    req = urllib.request.Request(URL, headers={'User-Agent': 'radar-eshop/1.0'})
    with urllib.request.urlopen(req, timeout=40) as r:
        html = r.read().decode('utf-8', 'replace')

    partes = html.split('<div class="tgme_widget_message_wrap')
    mensagens = []
    for parte in partes[1:]:
        post = re.search(r'data-post="([^"]+)"', parte)
        quando = re.search(r'<time datetime="([^"]+)"', parte)
        corpo = re.search(
            r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', parte, re.S)
        if not (post and quando and corpo):
            continue
        texto = re.sub(r'<br\s*/?>', '\n', corpo.group(1))
        texto = re.sub(r'<[^>]+>', '', texto)
        import html as H
        texto = H.unescape(texto).strip()
        mensagens.append({
            'url': 'https://t.me/%s' % post.group(1),
            'data': quando.group(1)[:10],
            'texto': texto,
        })
    return mensagens


def interpreta(msg):
    """Devolve (titulo, preco, loja) ou None."""
    linhas = [l.strip() for l in msg['texto'].split('\n') if l.strip()]
    if not linhas:
        return None
    titulo = linhas[0]
    preco = re.search(r'Pre[cç]o:\s*R\$\s*([\d.]+(?:,\d{2})?)', msg['texto'], re.I)
    if not preco:
        return None
    bruto = preco.group(1).replace('.', '').replace(',', '.')
    try:
        valor = float(bruto)
    except ValueError:
        return None
    if not 20 <= valor <= 3000:   # fora disso e erro de leitura, nao oferta
        return None
    loja = re.search(r'Loja:\s*([^\n(]+)', msg['texto'], re.I)
    return titulo, valor, (loja.group(1).strip() if loja else '?')


def main():
    simular = '--simular' in sys.argv
    with io.open('data.json', encoding='utf-8') as f:
        dados = json.load(f)

    achados = []
    for msg in busca_mensagens():
        lido = interpreta(msg)
        if not lido:
            continue
        titulo, valor, loja = lido
        for jogo in dados['games']:
            if casa(jogo['n'], titulo):
                achados.append((jogo, titulo, valor, loja, msg))

    mudou = False
    for jogo, titulo, valor, loja, msg in achados:
        anterior = jogo.get('physSrc') or {}
        if anterior.get('d', '') > msg['data']:
            continue          # ja temos informacao mais recente
        if jogo.get('phys') == valor and anterior.get('d') == msg['data']:
            continue
        jogo['phys'] = valor
        jogo['physSrc'] = {'t': titulo, 'loja': loja, 'url': msg['url'], 'd': msg['data']}
        mudou = True

    enc = sys.stdout.encoding or 'ascii'
    def fala(texto):
        sys.stdout.write(texto.encode(enc, 'replace').decode(enc) + '\n')

    fala('%d ofertas lidas do canal, %d casaram com a lista' % (
        len(busca_mensagens()), len(achados)))
    for jogo, titulo, valor, loja, msg in achados:
        fala('  %s -> R$ %.2f (%s, %s)' % (jogo['n'], valor, loja, msg['data']))

    if simular:
        fala('modo simulacao: data.json nao foi tocado')
        return
    if mudou:
        dados['physChecked'] = datetime.now(BRASILIA).strftime('%Y-%m-%d')
        precos = modulo_precos()
        bloco = precos.serializa(dados)
        with io.open('data.json', 'w', encoding='utf-8', newline='') as f:
            f.write(bloco)
        precos.escreve_html(bloco)
    fala('FISICO_MUDOU=%d' % (1 if mudou else 0))


if __name__ == '__main__':
    main()
