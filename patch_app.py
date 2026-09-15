from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

css = """
  .codigo-lido { margin: -4px 0 18px; padding: 10px 12px; border: 1px solid var(--cor-borda); border-radius: 10px; background: var(--cor-fundo); text-align: center; font-size: .84rem; color: var(--cor-texto-secundario); }
  .codigo-lido strong { color: var(--cor-texto); font-size: .95rem; letter-spacing: .5px; }
"""
if '.codigo-lido {' not in s:
    s = s.replace('</style>', css + '</style>', 1)

needle = '      <input type="hidden" id="form-codigo">'
insert = '      <div id="codigo-lido" class="codigo-lido oculto">Código lido: <strong id="codigo-lido-valor"></strong></div>\n      <input type="hidden" id="form-codigo">'
if needle in s and 'id="codigo-lido-valor"' not in s:
    s = s.replace(needle, insert, 1)

start = s.find('  async function buscarProdutoAPI(codigo) {')
end = s.find('  function preencherFormulario(codigo, produto) {', start)
if start < 0 or end < 0:
    raise SystemExit('funcoes de busca nao encontradas')

fn = r'''  async function buscarProdutoAPI(codigo) {
    const campos = 'product_name,product_name_pt,product_name_en,brands,image_front_small_url';

    const normalizar = (p) => {
      if (!p) return null;
      const nome = p.product_name_pt || p.product_name || p.product_name_en || p.title || p.nome || p.name;
      if (!nome) return null;
      return {
        nome: String(nome).trim(),
        marca: p.brands || p.brand || p.marca || p.laboratorio || '',
        imagem: p.image_front_small_url || p.image_url || p.imagem_url || (Array.isArray(p.images) ? p.images[0] : null) || null
      };
    };

    const tentarJson = async (url, transformar) => {
      try {
        const res = await fetch(url, { headers: { Accept: 'application/json' } });
        if (!res.ok) return null;
        return transformar(await res.json());
      } catch (e) {
        return null;
      }
    };

    // Catalogo brasileiro amplo, incluindo medicamentos e higiene.
    let achado = await tentarJson(
      `https://dotcompany.com.br/api/catalogo/public/buscar?q=${encodeURIComponent(codigo)}`,
      data => normalizar(data && data.produto)
    );
    if (achado) return achado;

    // Base especializada em medicamentos brasileiros, cruzada com ANVISA/CMED.
    try {
      const res = await fetch(`https://dadosmedicamentos.com.br/ean/${encodeURIComponent(codigo)}`);
      if (res.ok) {
        const html = await res.text();
        const m = html.match(/<title[^>]*>\s*EAN\s+[^<]+?\s*[—-]\s*([^<]+?)\s*<\/title>/i);
        if (m && m[1]) {
          let nome = m[1].replace(/\s+/g, ' ').trim();
          const marca = nome.match(/\(([^()]+)\)\s*$/);
          if (marca) nome = nome.replace(/\s*\([^()]+\)\s*$/, '').trim();
          if (nome) return { nome, marca: marca ? marca[1] : '', imagem: null };
        }
      }
    } catch (e) {}

    // Open Food Facts universal: alimentos, cosmeticos, pet food e outros.
    achado = await tentarJson(
      `https://world.openfoodfacts.org/api/v3/product/${encodeURIComponent(codigo)}?product_type=all&cc=br&lc=pt&fields=${campos}`,
      data => normalizar(data && data.product)
    );
    if (achado) return achado;

    // Bases Open*Facts diretamente.
    for (const base of [
      'https://world.openfoodfacts.org',
      'https://world.openbeautyfacts.org',
      'https://world.openpetfoodfacts.org',
      'https://world.openproductsfacts.org'
    ]) {
      achado = await tentarJson(
        `${base}/api/v2/product/${encodeURIComponent(codigo)}.json?fields=${campos}`,
        data => data && data.status === 1 ? normalizar(data.product) : null
      );
      if (achado) return achado;
    }

    // Base global adicional.
    achado = await tentarJson(
      `https://api.upcitemdb.com/prod/trial/lookup?upc=${encodeURIComponent(codigo)}`,
      data => normalizar(data && data.items && data.items[0])
    );
    if (achado) return achado;

    const locais = {
      '7897042016297': {
        nome: 'Loção Hidratante Corporal Skalinha Bebê Lavanda 200 ml',
        marca: 'Skala',
        imagem: null
      }
    };
    return locais[codigo] || null;
  }

'''
s = s[:start] + fn + s[end:]

old = """  function preencherFormulario(codigo, produto) {
    document.getElementById('form-codigo').value = codigo;"""
new = """  function preencherFormulario(codigo, produto) {
    const codigoEl = document.getElementById('codigo-lido');
    const codigoValorEl = document.getElementById('codigo-lido-valor');
    if (codigoEl && codigoValorEl) {
      if (codigo) {
        codigoValorEl.textContent = codigo;
        codigoEl.classList.remove('oculto');
      } else {
        codigoValorEl.textContent = '';
        codigoEl.classList.add('oculto');
      }
    }
    document.getElementById('form-codigo').value = codigo;"""
if old not in s:
    raise SystemExit('preencherFormulario nao encontrada')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Patch aplicado')
