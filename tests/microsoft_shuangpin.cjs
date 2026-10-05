const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
function context(source) {
  const ctx = vm.createContext({save: {allowDoublePinyin: 13}});
  vm.runInContext(source.replace('export const ', 'const ') +
    '\nthis.convert = generateDoublePinyin; this.single = generateDoublePinyinSingleChar; this.schemes = doublePinyin;', ctx);
  return ctx;
}
const original = context(input.original), patched = context(input.patched);
const plain = v => JSON.parse(JSON.stringify(v));
const words = (ctx, syllables) => plain(ctx.convert(syllables.map(s => [s]), syllables.length === 1)).map(v => v.word).sort();
function expect(syllables, expected) {
  assert.deepEqual(words(patched, syllables), expected.sort(), syllables.join(' '));
  for (const result of patched.convert(syllables.map(s => [s]), syllables.length === 1)) {
    const increments = [].concat(result.increments);
    assert.equal(increments.reduce((a, b) => a + b, 0), result.word.length);
    assert(increments.every(n => n === 2));
  }
}
for (const [s, codes] of Object.entries({lv:['ly'], nv:['ny'], lü:['ly'], nü:['ny'],
  lve:['lt','lv'], nve:['nt','nv'], lue:['lt','lv'], nue:['nt','nv'],
  lüe:['lt','lv'], nüe:['nt','nv'], ju:['ju','jy'], qu:['qu','qy'],
  xu:['xu','xy'], yu:['yu','yy'], jv:['ju','jy'], qv:['qu','qy'],
  xv:['xu','xy'], yv:['yu','yy']})) expect([s], codes);
const zero = {a:'oa',ai:'ol',an:'oj',ang:'oh',ao:'ok',e:'oe',ei:'oz',en:'of',eng:'og',er:'or',o:'oo',ou:'ob'};
for (const [s, code] of Object.entries(zero)) expect([s], [code]);
// Independent key chart: exercise every ordinary final and all initials.
const finals = {a:['a'],o:['o'],e:['e'],i:['i'],u:['u'],ai:['l'],an:['j'],ang:['h'],ao:['k'],
  ei:['z'],en:['f'],eng:['g'],ia:['w'],ian:['m'],iang:['d'],iao:['c'],ie:['x'],iong:['s'],
  in:['n'],ing:[';'],iu:['q'],ong:['s'],ou:['b'],ua:['w'],uai:['y'],uan:['r'],uang:['d'],
  ue:['t','v'],ui:['v'],un:['p'],uo:['o'],ve:['t','v']};
let chartChecks = 0;
for (const initial of ['b','p','m','f','d','t','n','l','g','k','h','j','q','x','zh','ch','sh','r','z','c','s','y','w']) {
  for (const [final, keys] of Object.entries(finals)) {
    const syllable = initial + final;
    if (['ju','qu','xu','yu'].includes(syllable)) continue;
    const first = {zh:'v',ch:'i',sh:'u'}[initial] || initial;
    expect([syllable], keys.map(k => first + k));
    chartChecks++;
  }
}
// Every other scheme must remain identical, including its existing behavior.
let regressionChecks = 0;
const samples = [...Object.keys(zero), 'lv','nv','ju','qu','xu','yu'];
for (const initial of ['b','p','m','f','d','t','n','l','g','k','h','j','q','x','zh','ch','sh','r','z','c','s','y','w'])
  for (const final of Object.keys(finals)) samples.push(initial + final);
for (let i = 0; i < original.schemes.length; i++) {
  if (i === 13) continue;
  assert.deepEqual(plain(patched.schemes[i]), plain(original.schemes[i]));
  for (const s of samples) {
    assert.deepEqual(plain(patched.single(s, patched.schemes[i])), plain(original.single(s, original.schemes[i])));
    regressionChecks++;
  }
}
vm.runInContext(input.pinyin.replace('export class ', 'class ') + '\nthis.py = new Pinyin();', patched);
const cases = {'旅客':['lyke'],'女儿':['nyor'],'绿色':['lyse'],'略微':['ltwz','lvwz'],
  '虐待':['ntdl','nvdl'],'居住':['juvu','jyvu'],'区域':['quyu','quyy','qyyu','qyyy'],
  '需要':['xuyk','xyyk'],'语言':['yuyj','yyyj'],'明天':['m;tm'],'安全':['ojqr']};
for (const [word, expected] of Object.entries(cases)) {
  const syllables = plain(patched.py.pinyin(word, {style:patched.py.STYLE_NORMAL, segment:'segmentit', heteronym:false})).map(p => p[0]);
  expect(syllables, expected);
  console.log(word + ': ' + words(patched, syllables).join(' / '));
}
expect(['lv','nv','lve','nve'], ['lynyltnt','lynyltnv','lynylvnt','lynylvnv']);
patched.save.allowDoublePinyin = null;
assert.deepEqual(plain(patched.convert([['lv']], true)), []);
console.log(`PASS: ${chartChecks} key-chart cases, ${regressionChecks} other-scheme regression cases, special syllables, words, increments and disabled mode.`);
