const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const root = path.join(__dirname, '..');
const esc = (value) => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

function readCsv(filename) {
  return fs.readFileSync(filename, 'utf8').trim().split(/\r?\n/).map((row) => row.split(','));
}

function scale(value, low, high, start, end) {
  return start + ((value - low) / (high - low)) * (end - start);
}

async function renderGamut() {
  const rows = readCsv(path.join(__dirname, 'source', 'CIE_xyz_1931_2deg.csv')).map((r) => r.map(Number));
  const points = rows.filter(([wave]) => wave >= 380 && wave <= 700).map(([wave, xbar, ybar, zbar]) => {
    const total = xbar + ybar + zbar;
    return [xbar / total, ybar / total, wave];
  });
  const x = (v) => scale(v, 0, 0.8, 95, 805).toFixed(1);
  const y = (v) => scale(v, 0.9, 0, 65, 765).toFixed(1);
  const outline = points.map(([px, py]) => `${x(px)},${y(py)}`).join(' ');
  const polygon = `${outline} ${x(points[0][0])},${y(points[0][1])}`;
  const gamuts = [
    ['sRGB (standard monitors)', '#264653', [[.640,.330],[.300,.600],[.150,.060]]],
    ['Display P3 (Apple screens)', '#e76f51', [[.680,.320],[.265,.690],[.150,.060]]],
    ['Adobe RGB (photo monitors)', '#2a9d8f', [[.640,.330],[.210,.710],[.150,.060]]],
    ['Rec.2020 (UHD televisions)', '#6a4c93', [[.708,.292],[.170,.797],[.131,.046]]],
  ];
  const triangles = gamuts.map(([name, colour, vertices]) => {
    const coords = vertices.map(([px, py]) => `${x(px)},${y(py)}`).join(' ');
    return `<polygon points="${coords}" fill="none" stroke="${colour}" stroke-width="4"/><text x="835" y="${112 + gamuts.indexOf(gamuts.find((g) => g[0] === name)) * 34}" font-size="18" fill="${colour}">● ${esc(name)}</text>`;
  }).join('');
  const wavelengthLabels = [[380, '380 nm'], [450, '450'], [500, '500'], [550, '550'], [600, '600'], [650, '650'], [700, '700']].map(([wave, label]) => {
    const item = points.find((point) => point[2] === wave);
    return item ? `<circle cx="${x(item[0])}" cy="${y(item[1])}" r="3" fill="#333"/><text x="${Number(x(item[0])) + 7}" y="${Number(y(item[1])) - 7}" font-size="13" fill="#333">${label}</text>` : '';
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="860" viewBox="0 0 1280 860">
  <defs><linearGradient id="locus" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#5e60ce"/><stop offset=".35" stop-color="#00b4d8"/><stop offset=".58" stop-color="#80b918"/><stop offset=".78" stop-color="#f9c74f"/><stop offset="1" stop-color="#d62828"/></linearGradient></defs>
  <rect width="1280" height="860" fill="#fffdf8"/><text x="95" y="38" font-family="Arial" font-size="28" font-weight="700" fill="#222">Four display gamuts on the CIE 1931 chromaticity diagram</text>
  <text x="95" y="62" font-family="Arial" font-size="16" fill="#555">Filled spectral locus; chromaticities x and y</text>
  <rect x="95" y="65" width="710" height="700" fill="#f8f8f8" stroke="#555"/>
  <polygon points="${polygon}" fill="url(#locus)" fill-opacity=".22" stroke="#222" stroke-width="3"/>
  <line x1="${x(points[0][0])}" y1="${y(points[0][1])}" x2="${x(points.at(-1)[0])}" y2="${y(points.at(-1)[1])}" stroke="#222" stroke-width="3" stroke-dasharray="7 5"/>
  ${wavelengthLabels}${triangles}
  <text x="450" y="820" font-family="Arial" font-size="20" text-anchor="middle">x chromaticity</text><text x="35" y="420" font-family="Arial" font-size="20" text-anchor="middle" transform="rotate(-90 35 420)">y chromaticity</text>
  <text x="835" y="78" font-family="Arial" font-size="21" font-weight="700" fill="#222">Screen gamut</text><text x="835" y="268" font-family="Arial" font-size="15" fill="#555">Each triangle joins a display's RGB primaries.</text>
  <text x="835" y="302" font-family="Arial" font-size="15" fill="#555">Source: CIE 1931 2° observer data supplied</text><text x="835" y="325" font-family="Arial" font-size="15" fill="#555">with 36104 Session 2, Part A.</text></svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, 'part_a_gamut_comparison.png'));
}

function dot(a, b) { return a.reduce((sum, v, i) => sum + v * b[i], 0); }
function matVec(matrix, vector) { return matrix.map((row) => dot(row, vector)); }
function norm(vector) { return Math.sqrt(dot(vector, vector)); }
function pca2(vectors) {
  const n = vectors.length, d = vectors[0].length;
  const mean = Array.from({length:d}, (_, j) => vectors.reduce((s, row) => s + row[j], 0) / n);
  const centered = vectors.map((row) => row.map((v, j) => v - mean[j]));
  const covariance = Array.from({length:d}, (_, i) => Array.from({length:d}, (_, j) => centered.reduce((s, row) => s + row[i] * row[j], 0) / (n - 1)));
  const power = (orthogonalTo) => {
    let v = Array.from({length:d}, (_, i) => ((i * 17 + 11) % 19) / 19 - .5);
    for (let iteration = 0; iteration < 150; iteration += 1) {
      v = matVec(covariance, v);
      if (orthogonalTo) { const projection = dot(v, orthogonalTo); v = v.map((x, i) => x - projection * orthogonalTo[i]); }
      const length = norm(v); v = v.map((x) => x / length);
    }
    return v;
  };
  const one = power(); const two = power(one);
  return centered.map((row) => [dot(row, one), dot(row, two)]);
}

async function renderEmbeddings() {
  const table = new Map(readCsv(path.join(__dirname, 'source', 'glove_words_50d.csv')).map(([word, ...values]) => [word, values.map(Number)]));
  const pairs = [['cat','cats'], ['dog','dogs'], ['car','cars'], ['child','children']];
  const words = pairs.flat();
  const projected = pca2(words.map((word) => table.get(word)));
  const xs = projected.map((p) => p[0]); const ys = projected.map((p) => p[1]);
  const xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  const x = (value) => scale(value, xmin - .3, xmax + .3, 100, 880).toFixed(1);
  const y = (value) => scale(value, ymax + .3, ymin - .3, 95, 650).toFixed(1);
  const labelNudge = {
    cat: [-12, -24, 'end'], cats: [12, 48, 'start'],
    dog: [-12, 54, 'end'], dogs: [12, -20, 'start'],
    car: [-12, -12, 'end'], cars: [12, -12, 'start'],
    child: [-12, -12, 'end'], children: [12, -12, 'start'],
  };
  const annotations = words.map((word, i) => {
    const [dx, dy, anchor] = labelNudge[word];
    return `<circle cx="${x(projected[i][0])}" cy="${y(projected[i][1])}" r="7" fill="#264653"/><text x="${Number(x(projected[i][0])) + dx}" y="${Number(y(projected[i][1])) + dy}" text-anchor="${anchor}" font-size="19" fill="#222">${word}</text>`;
  }).join('');
  const arrows = pairs.map((_, i) => {
    const a = projected[i * 2], b = projected[i * 2 + 1];
    return `<line x1="${x(a[0])}" y1="${y(a[1])}" x2="${x(b[0])}" y2="${y(b[1])}" stroke="#c0448f" stroke-width="3" marker-end="url(#arrow)"/>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="760" viewBox="0 0 1020 760"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#c0448f"/></marker></defs><rect width="1020" height="760" fill="#fffdf8"/><text x="65" y="45" font-family="Arial" font-size="28" font-weight="700">Singular → plural nouns in GloVe embeddings</text><text x="65" y="70" font-family="Arial" font-size="16" fill="#555">PCA projection of the Session 2 supplied 50-dimensional word vectors</text><rect x="100" y="95" width="780" height="555" fill="#f8f8f8" stroke="#555"/>${arrows}${annotations}<text x="490" y="705" text-anchor="middle" font-family="Arial" font-size="19">first principal component</text><text x="35" y="385" text-anchor="middle" font-family="Arial" font-size="19" transform="rotate(-90 35 385)">second principal component</text><text x="100" y="735" font-family="Arial" font-size="15" fill="#555">Relation: singular noun to plural noun (four original pairs)</text></svg>`;
  await sharp(Buffer.from(svg)).png().toFile(path.join(__dirname, 'part_b_plural_nouns.png'));
}

Promise.all([renderGamut(), renderEmbeddings()]).then(() => console.log('Created Part A and Part B PNG artefacts.'));
