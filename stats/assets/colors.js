// ═══════════════════════════════════════
// PLAYER IDENTITY PALETTE
// ═══════════════════════════════════════
// 8 curated hues for the first 8 players - intentionally excludes the brand
// accent (#7c6aef) so the player-dot stays visible on the active nav button.
// The palette already fills most of the hue wheel, so adding *new* hues for
// overflow players always lands near an existing one. Instead we reuse each
// palette hue at a very different lightness: pass 1 uses pastels (L=82),
// pass 2 uses dark (L=40). That gives 24 visually distinct identities before
// any duplication, without creating indistinguishable near-hues.
const PALETTE = ['#3ecf8e','#ef6a6a','#efaa6a','#6aafef','#ef6ac0','#6aefd9','#efd96a','#a86aef'];
const _PALETTE_HUES = [153, 0, 29, 209, 321, 170, 50, 268];
function _hslHex(h,s,l){s/=100;l/=100;const a=s*Math.min(l,1-l);const f=n=>{const k=(n+h/30)%12;return Math.round(255*(l-a*Math.max(-1,Math.min(k-3,9-k,1)))).toString(16).padStart(2,'0')};return '#'+f(0)+f(8)+f(4)}
function playerColor(i){
  if(i<PALETTE.length)return PALETTE[i];
  const pass=Math.floor(i/PALETTE.length);
  const h=_PALETTE_HUES[i%PALETTE.length];
  const l=pass===1?82:pass===2?40:60;
  return _hslHex(h,70,l);
}

// ═══════════════════════════════════════
// CHART PALETTE - shared fallback hues for categorical chart slices
// ═══════════════════════════════════════
// Unified 15-color array replacing 4 previously-inline palettes (death-causes
// doughnut, distance-type stacked bar, per-player distance bar, treemap
// fallback). First 8 mirror the identity PALETTE (but start with brand violet
// #7c6aef since no player-identity overlap matters here), then 7 additional
// muted/darkened hues to reach 15 - matches the longest original inline array
// (treemap fallback) so no chart loses distinct hues.
const CHART_PALETTE = [
  '#7c6aef', '#3ecf8e', '#ef6a6a', '#efaa6a',
  '#6aafef', '#6aefd9', '#efd96a', '#ef6ac0',
  '#a86aef', '#5a9e6f', '#9e5a5a', '#5a6f9e',
  '#9e8b5a', '#5a9e9e', '#8b8b96'
];

// ═══════════════════════════════════════
// BLOCK → COLOR MAP - approximate in-game hue per block id
// ═══════════════════════════════════════
// Used by the treemap so rects hint at what you're looking at (grey for
// stone, green for grass, dark red for netherrack, …). Explicit entries
// cover the blocks most commonly mined; suffix helpers catch colored
// variants (16 wools × 3 material families = 48 keys we don't list by
// hand) and wood / leaf families. Unknowns fall back to the rainbow
// palette so variety is preserved.
const DYE_COLORS={white:'#f0f0f0',orange:'#f9801d',magenta:'#c74ebd',light_blue:'#3ab3da',yellow:'#fed83d',lime:'#80c71f',pink:'#f38baa',gray:'#474f52',light_gray:'#9d9d97',cyan:'#169c9c',purple:'#8932b8',blue:'#3c44aa',brown:'#835432',green:'#5e7c16',red:'#b02e26',black:'#1d1d21'};
const WOOD_COLORS={oak:'#b08a50',spruce:'#725232',birch:'#d7cfa0',jungle:'#b08545',acacia:'#b8713e',dark_oak:'#402919',mangrove:'#763431',cherry:'#e2aba2',pale_oak:'#d4c6a8',bamboo:'#c4b962',crimson:'#6a2e46',warped:'#2d8b7f'};
const LEAF_COLORS={oak:'#4a7829',spruce:'#4b6440',birch:'#6d8a4a',jungle:'#2f8a1b',acacia:'#4e802e',dark_oak:'#365923',mangrove:'#78aa3f',cherry:'#e49dbc',pale_oak:'#a8b3a0',azalea:'#6aa03b',flowering_azalea:'#e493cb'};
const BLOCK_COLORS={
  stone:'#7e7e7e',cobblestone:'#6e6e6e',deepslate:'#494b4d',cobbled_deepslate:'#3f4143',
  tuff:'#6a6966',andesite:'#888784',diorite:'#c9c8c3',granite:'#9d6b56',calcite:'#d8d8d4',
  basalt:'#4e4e54',smooth_basalt:'#52525a',blackstone:'#2e292e',stone_bricks:'#7a7a7a',
  dripstone_block:'#876d5e',amethyst_block:'#866cb6',
  dirt:'#8b6a3f',grass_block:'#6aa03b',coarse_dirt:'#7c5a36',rooted_dirt:'#916b4d',
  podzol:'#6b4a2a',mycelium:'#847581',mud:'#3e3127',sand:'#dbd0a6',red_sand:'#b8552a',
  gravel:'#828282',clay:'#a3a8b3',packed_mud:'#9c7c5b',mud_bricks:'#8c6e4f',
  farmland:'#524022',dirt_path:'#7a5f2f',
  netherrack:'#6b2a26',nether_gold_ore:'#7d3a2e',ancient_debris:'#513431',
  crimson_nylium:'#841919',warped_nylium:'#1f7566',soul_sand:'#3f2f23',soul_soil:'#4e3929',
  nether_quartz_ore:'#9a7a70',nether_wart_block:'#751413',warped_wart_block:'#167272',
  snow:'#fafefe',snow_block:'#f5fcff',ice:'#8ec3e8',packed_ice:'#85b6df',blue_ice:'#6fa4e8',
  coal_ore:'#373737',iron_ore:'#c6ad97',gold_ore:'#d6bc4d',diamond_ore:'#5ecfd5',
  emerald_ore:'#2cb85c',lapis_ore:'#3058bb',redstone_ore:'#c13c3c',copper_ore:'#c27a4b',
  deepslate_coal_ore:'#2a2d30',deepslate_iron_ore:'#796e5c',deepslate_gold_ore:'#a4883b',
  deepslate_diamond_ore:'#3a8e94',deepslate_emerald_ore:'#208a48',deepslate_lapis_ore:'#2e4d90',
  deepslate_redstone_ore:'#8c2d2d',deepslate_copper_ore:'#8a5535',
  sculk:'#111828',sculk_vein:'#0e1621',moss_block:'#5d743c',short_grass:'#7c9b4c',
  sugar_cane:'#82b84a',wheat:'#d8ca6e',bamboo:'#879430',pumpkin:'#d88926',melon:'#a5ca2a',
  sandstone:'#d6ca79',red_sandstone:'#a9481f',
  terracotta:'#975c42',obsidian:'#110d1b',end_stone:'#e0dba1',scaffolding:'#c6a477',
  torch:'#e3b94a',glowstone:'#d2ab55',brown_mushroom_block:'#966e56',red_mushroom_block:'#c64a42',
  mangrove_roots:'#5a4131',bamboo_block:'#6f7a26',
  shulker_box:'#704e70'
};
const DYE_SUFFIXES=['_wool','_concrete','_concrete_powder','_terracotta','_stained_glass','_stained_glass_pane','_glazed_terracotta','_carpet','_shulker_box','_candle','_bed'];
const WOOD_SUFFIXES=['_log','_wood','_planks','_stem','_hyphae','_fence','_door','_slab','_stairs','_trapdoor'];
function blockColor(key,fallback){
  if(BLOCK_COLORS[key]) return BLOCK_COLORS[key];
  const bare=key.startsWith('stripped_')?key.slice(9):key;
  for(const suf of WOOD_SUFFIXES){
    if(bare.endsWith(suf)){
      const sp=bare.slice(0,-suf.length);
      if(WOOD_COLORS[sp]) return WOOD_COLORS[sp];
    }
  }
  if(key.endsWith('_leaves')){
    const sp=key.slice(0,-7);
    if(LEAF_COLORS[sp]) return LEAF_COLORS[sp];
  }
  for(const suf of DYE_SUFFIXES){
    if(key.endsWith(suf)){
      const sp=key.slice(0,-suf.length);
      if(DYE_COLORS[sp]) return DYE_COLORS[sp];
    }
  }
  return fallback;
}
