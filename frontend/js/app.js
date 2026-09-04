// State
let beamConfig = {
  length: 6.0,
  elasticModulus: 200.0,
  momentOfInertia: 83.3
};

let supportsList = [
  { id: 'S1', type: 'pin', position: 0.0 },
  { id: 'S2', type: 'roller', position: 6.0 }
];

let loadsList = [
  { id: 'L1', type: 'point', magnitude: 20.0, position: 3.0, start_pos: 0.0, end_pos: 0.0, start_magnitude: 0.0, end_magnitude: 0.0 }
];

let chartInstances = {};
let presetsData = [];

// DOM Elements
const beamLengthInput = document.getElementById('beamLength');
const materialSelect = document.getElementById('materialSelect');
const elasticModulusInput = document.getElementById('elasticModulus');
const momentOfInertiaInput = document.getElementById('momentOfInertia');
const presetSelect = document.getElementById('presetSelect');
const supportsBody = document.getElementById('supportsBody');
const loadsBody = document.getElementById('loadsBody');
const btnAddSupport = document.getElementById('btnAddSupport');
const btnAddLoad = document.getElementById('btnAddLoad');
const btnCalculate = document.getElementById('btnCalculate');
const btnReset = document.getElementById('btnReset');
const btnExport = document.getElementById('btnExport');
const beamCanvas = document.getElementById('beamCanvas');

// Section Calculator Modal Elements
const btnSectionCalc = document.getElementById('btnSectionCalc');
const sectionModal = document.getElementById('sectionModal');
const btnCloseModal = document.getElementById('btnCloseModal');
const sectionTypeSelect = document.getElementById('sectionTypeSelect');
const sectionInputs = document.getElementById('sectionInputs');
const sectionResult = document.getElementById('sectionResult');
const btnApplySection = document.getElementById('btnApplySection');
let currentCalculatedI = null;

const MATERIAL_E = {
  structural_steel: 200.0,
  stainless_steel: 193.0,
  aluminum_6061: 69.0,
  structural_timber: 12.0,
  concrete_c30: 30.0
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  renderSupportsTable();
  renderLoadsTable();
  renderSectionModalInputs();
  drawSchematic();
  await loadPresets();
  calculateBeam();
});

function setupEventListeners() {
  beamLengthInput.addEventListener('input', (e) => {
    beamConfig.length = parseFloat(e.target.value) || 1.0;
    drawSchematic();
  });

  materialSelect.addEventListener('change', (e) => {
    const mat = e.target.value;
    if (MATERIAL_E[mat]) {
      elasticModulusInput.value = MATERIAL_E[mat];
      beamConfig.elasticModulus = MATERIAL_E[mat];
    }
  });

  elasticModulusInput.addEventListener('input', (e) => {
    beamConfig.elasticModulus = parseFloat(e.target.value) || 200.0;
  });

  momentOfInertiaInput.addEventListener('input', (e) => {
    beamConfig.momentOfInertia = parseFloat(e.target.value) || 83.3;
  });

  btnAddSupport.addEventListener('click', () => {
    const nextId = 'S' + (supportsList.length + 1);
    supportsList.push({ id: nextId, type: 'roller', position: beamConfig.length });
    renderSupportsTable();
    drawSchematic();
  });

  btnAddLoad.addEventListener('click', () => {
    const nextId = 'L' + (loadsList.length + 1);
    loadsList.push({
      id: nextId,
      type: 'point',
      magnitude: 10.0,
      position: Math.round((beamConfig.length / 2.0) * 10) / 10,
      start_pos: 0.0,
      end_pos: beamConfig.length,
      start_magnitude: 10.0,
      end_magnitude: 10.0
    });
    renderLoadsTable();
    drawSchematic();
  });

  btnCalculate.addEventListener('click', calculateBeam);

  btnReset.addEventListener('click', () => {
    beamConfig.length = 6.0;
    beamConfig.elasticModulus = 200.0;
    beamConfig.momentOfInertia = 83.3;
    beamLengthInput.value = 6.0;
    elasticModulusInput.value = 200.0;
    momentOfInertiaInput.value = 83.3;
    materialSelect.value = 'structural_steel';

    supportsList = [
      { id: 'S1', type: 'pin', position: 0.0 },
      { id: 'S2', type: 'roller', position: 6.0 }
    ];

    loadsList = [
      { id: 'L1', type: 'point', magnitude: 20.0, position: 3.0, start_pos: 0.0, end_pos: 0.0, start_magnitude: 0.0, end_magnitude: 0.0 }
    ];

    renderSupportsTable();
    renderLoadsTable();
    drawSchematic();
    calculateBeam();
  });

  btnExport.addEventListener('click', () => {
    window.print();
  });

  btnSectionCalc.addEventListener('click', () => {
    sectionModal.classList.remove('hidden');
    updateSectionCalculation();
  });

  btnCloseModal.addEventListener('click', () => {
    sectionModal.classList.add('hidden');
  });

  sectionTypeSelect.addEventListener('change', () => {
    renderSectionModalInputs();
    updateSectionCalculation();
  });

  btnApplySection.addEventListener('click', () => {
    if (currentCalculatedI !== null) {
      momentOfInertiaInput.value = currentCalculatedI;
      beamConfig.momentOfInertia = currentCalculatedI;
      sectionModal.classList.add('hidden');
    }
  });

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.classList.toggle('active');
      const chartType = btn.getAttribute('data-chart');
      const map = {
        sfd: 'boxSFD',
        bmd: 'boxBMD',
        deflection: 'boxDeflection',
        slope: 'boxSlope'
      };
      const targetBox = document.getElementById(map[chartType]);
      if (targetBox) {
        targetBox.classList.toggle('hidden', !btn.classList.contains('active'));
      }
    });
  });

  window.addEventListener('resize', () => {
    drawSchematic();
  });
}

// Load Presets from API
async function loadPresets() {
  try {
    const res = await fetch('/api/presets');
    if (!res.ok) return;
    const data = await res.json();
    presetsData = data.presets || [];

    presetSelect.innerHTML = '<option value="" disabled selected>-- Select an Engineering Preset --</option>';
    presetsData.forEach((preset, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = [] ;
      presetSelect.appendChild(opt);
    });

    presetSelect.addEventListener('change', (e) => {
      const idx = parseInt(e.target.value);
      if (presetsData[idx]) {
        loadPresetData(presetsData[idx]);
      }
    });
  } catch (err) {
    console.error('Failed to fetch presets:', err);
  }
}

function loadPresetData(p) {
  beamConfig.length = p.beam.length;
  beamConfig.elasticModulus = p.beam.elastic_modulus;
  beamConfig.momentOfInertia = p.beam.moment_of_inertia;

  beamLengthInput.value = p.beam.length;
  elasticModulusInput.value = p.beam.elastic_modulus;
  momentOfInertiaInput.value = p.beam.moment_of_inertia;

  supportsList = p.supports.map((s, idx) => ({
    id: S,
    type: s.type,
    position: s.position
  }));

  loadsList = p.loads.map((l, idx) => ({
    id: L,
    type: l.type,
    magnitude: l.magnitude || 0.0,
    position: l.position !== undefined ? l.position : 0.0,
    start_pos: l.start_pos !== undefined ? l.start_pos : 0.0,
    end_pos: l.end_pos !== undefined ? l.end_pos : p.beam.length,
    start_magnitude: l.start_magnitude !== undefined ? l.start_magnitude : (l.magnitude || 0.0),
    end_magnitude: l.end_magnitude !== undefined ? l.end_magnitude : (l.magnitude || 0.0)
  }));

  renderSupportsTable();
  renderLoadsTable();
  drawSchematic();
  calculateBeam();
}

function renderSupportsTable() {
  supportsBody.innerHTML = '';
  supportsList.forEach((s, idx) => {
    const tr = document.createElement('tr');
    tr.innerHTML = 
      <td>
        <select class="sup-type" data-idx="">
          <option value="pin" >Pin (Δy)</option>
          <option value="roller" >Roller (Δy)</option>
          <option value="fixed" >Fixed (Δy, θ)</option>
        </select>
      </td>
      <td>
        <input type="number" class="sup-pos" data-idx="" value="" min="0" max="" step="0.2">
      </td>
      <td>
        <button class="btn-del" data-idx="" title="Remove support">&times;</button>
      </td>
    ;
    supportsBody.appendChild(tr);
  });

  supportsBody.querySelectorAll('.sup-type').forEach(el => {
    el.addEventListener('change', (e) => {
      const idx = e.target.getAttribute('data-idx');
      supportsList[idx].type = e.target.value;
      drawSchematic();
    });
  });

  supportsBody.querySelectorAll('.sup-pos').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      supportsList[idx].position = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  supportsBody.querySelectorAll('.btn-del').forEach(el => {
    el.addEventListener('click', (e) => {
      const idx = e.target.getAttribute('data-idx');
      supportsList.splice(idx, 1);
      renderSupportsTable();
      drawSchematic();
    });
  });
}

function renderLoadsTable() {
  loadsBody.innerHTML = '';
  loadsList.forEach((l, idx) => {
    const tr = document.createElement('tr');
    let magField = '';
    let posField = '';

    if (l.type === 'point') {
      magField = <input type="number" class="load-mag" data-idx="" value="" step="1.0" placeholder="kN">;
      posField = <input type="number" class="load-pos" data-idx="" value="" min="0" max="" step="0.2" placeholder="x (m)">;
    } else if (l.type === 'udl') {
      magField = <input type="number" class="load-mag" data-idx="" value="" step="1.0" placeholder="kN/m">;
      posField = <div style="display:flex;gap:4px;">
        <input type="number" class="load-x1" data-idx="" value="" min="0" step="0.2" placeholder="x1">
        <input type="number" class="load-x2" data-idx="" value="" min="0" step="0.2" placeholder="x2">
      </div>;
    } else if (l.type === 'uvl') {
      magField = <div style="display:flex;gap:4px;">
        <input type="number" class="load-w1" data-idx="" value="" step="1.0" placeholder="w1">
        <input type="number" class="load-w2" data-idx="" value="" step="1.0" placeholder="w2">
      </div>;
      posField = <div style="display:flex;gap:4px;">
        <input type="number" class="load-x1" data-idx="" value="" min="0" step="0.2" placeholder="x1">
        <input type="number" class="load-x2" data-idx="" value="" min="0" step="0.2" placeholder="x2">
      </div>;
    } else if (l.type === 'moment') {
      magField = <input type="number" class="load-mag" data-idx="" value="" step="1.0" placeholder="kN·m">;
      posField = <input type="number" class="load-pos" data-idx="" value="" min="0" max="" step="0.2" placeholder="x (m)">;
    }

    tr.innerHTML = 
      <td>
        <select class="load-type" data-idx="">
          <option value="point" >Point (kN)</option>
          <option value="udl" >UDL (kN/m)</option>
          <option value="uvl" >UVL (kN/m)</option>
          <option value="moment" >Moment (kN·m)</option>
        </select>
      </td>
      <td></td>
      <td></td>
      <td>
        <button class="btn-del" data-idx="" title="Remove load">&times;</button>
      </td>
    ;
    loadsBody.appendChild(tr);
  });

  loadsBody.querySelectorAll('.load-type').forEach(el => {
    el.addEventListener('change', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].type = e.target.value;
      renderLoadsTable();
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-mag').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      const val = parseFloat(e.target.value) || 0.0;
      loadsList[idx].magnitude = val;
      loadsList[idx].start_magnitude = val;
      loadsList[idx].end_magnitude = val;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-w1').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].start_magnitude = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-w2').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].end_magnitude = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-pos').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].position = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-x1').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].start_pos = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.load-x2').forEach(el => {
    el.addEventListener('input', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList[idx].end_pos = parseFloat(e.target.value) || 0.0;
      drawSchematic();
    });
  });

  loadsBody.querySelectorAll('.btn-del').forEach(el => {
    el.addEventListener('click', (e) => {
      const idx = e.target.getAttribute('data-idx');
      loadsList.splice(idx, 1);
      renderLoadsTable();
      drawSchematic();
    });
  });
}

function renderSectionModalInputs() {
  const type = sectionTypeSelect.value;
  if (type === 'rectangle') {
    sectionInputs.innerHTML = 
      <div class="form-group">
        <label>Width b (mm)</label>
        <input type="number" id="sec_b" value="100" class="form-input">
      </div>
      <div class="form-group">
        <label>Height h (mm)</label>
        <input type="number" id="sec_h" value="200" class="form-input">
      </div>
    ;
  } else if (type === 'solid_circle') {
    sectionInputs.innerHTML = 
      <div class="form-group">
        <label>Diameter d (mm)</label>
        <input type="number" id="sec_d" value="150" class="form-input">
      </div>
    ;
  } else if (type === 'hollow_circle') {
    sectionInputs.innerHTML = 
      <div class="form-group">
        <label>Outer Dia D (mm)</label>
        <input type="number" id="sec_do" value="150" class="form-input">
      </div>
      <div class="form-group">
        <label>Inner Dia d (mm)</label>
        <input type="number" id="sec_di" value="130" class="form-input">
      </div>
    ;
  } else if (type === 'i_beam') {
    sectionInputs.innerHTML = 
      <div class="form-group">
        <label>Flange Width bf (mm)</label>
        <input type="number" id="sec_bf" value="150" class="form-input">
      </div>
      <div class="form-group">
        <label>Total Depth h (mm)</label>
        <input type="number" id="sec_tot_h" value="300" class="form-input">
      </div>
      <div class="form-group">
        <label>Flange Thick tf (mm)</label>
        <input type="number" id="sec_tf" value="12" class="form-input">
      </div>
      <div class="form-group">
        <label>Web Thick tw (mm)</label>
        <input type="number" id="sec_tw" value="8" class="form-input">
      </div>
    ;
  }

  sectionInputs.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('input', updateSectionCalculation);
  });
}

async function updateSectionCalculation() {
  const type = sectionTypeSelect.value;
  let params = {};
  if (type === 'rectangle') {
    params.width_mm = parseFloat(document.getElementById('sec_b')?.value) || 100;
    params.height_mm = parseFloat(document.getElementById('sec_h')?.value) || 200;
  } else if (type === 'solid_circle') {
    params.diameter_mm = parseFloat(document.getElementById('sec_d')?.value) || 150;
  } else if (type === 'hollow_circle') {
    params.outer_diameter_mm = parseFloat(document.getElementById('sec_do')?.value) || 150;
    params.inner_diameter_mm = parseFloat(document.getElementById('sec_di')?.value) || 130;
  } else if (type === 'i_beam') {
    params.flange_width_mm = parseFloat(document.getElementById('sec_bf')?.value) || 150;
    params.total_height_mm = parseFloat(document.getElementById('sec_tot_h')?.value) || 300;
    params.flange_thickness_mm = parseFloat(document.getElementById('sec_tf')?.value) || 12;
    params.web_thickness_mm = parseFloat(document.getElementById('sec_tw')?.value) || 8;
  }

  try {
    const res = await fetch('/api/section-calculator', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ section_type: type, parameters: params })
    });
    if (res.ok) {
      const data = await res.json();
      const p = data.properties;
      currentCalculatedI = p.moment_of_inertia_1e6_mm4;
      sectionResult.innerHTML = 
        <div><strong>Moment of Inertia I:</strong>  &times; 10⁶ mm⁴ ( m⁴)</div>
        <div><strong>Section Modulus Z:</strong>  cm³ | <strong>Area A:</strong>  cm²</div>
      ;
    }
  } catch (err) {
    console.error(err);
  }
}

// 2D Live Schematic Canvas Rendering
function drawSchematic() {
  if (!beamCanvas) return;
  const ctx = beamCanvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = beamCanvas.getBoundingClientRect();

  beamCanvas.width = rect.width * dpr;
  beamCanvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  const L = beamConfig.length || 1.0;
  const marginX = 60;
  const beamY = 115;
  const beamH = 14;
  const drawW = w - 2 * marginX;

  function toCanvasX(xVal) {
    return marginX + (Math.max(0, Math.min(L, xVal)) / L) * drawW;
  }

  // 1. Draw Beam Member
  const beamGrad = ctx.createLinearGradient(0, beamY - beamH/2, 0, beamY + beamH/2);
  beamGrad.addColorStop(0, '#64748b');
  beamGrad.addColorStop(0.5, '#94a3b8');
  beamGrad.addColorStop(1, '#475569');

  ctx.fillStyle = beamGrad;
  ctx.strokeStyle = '#cbd5e1';
  ctx.lineWidth = 1.5;

  ctx.beginPath();
  ctx.roundRect(marginX, beamY - beamH / 2, drawW, beamH, 3);
  ctx.fill();
  ctx.stroke();

  // 2. Draw Supports
  supportsList.forEach(s => {
    const sx = toCanvasX(s.position);
    const sy = beamY + beamH / 2;

    if (s.type === 'pin') {
      ctx.fillStyle = '#38bdf8';
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx - 12, sy + 20);
      ctx.lineTo(sx + 12, sy + 20);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx - 16, sy + 22);
      ctx.lineTo(sx + 16, sy + 22);
      ctx.stroke();

      drawGroundHatch(ctx, sx - 16, sx + 16, sy + 22);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(${s.position}m, sx, sy + 38);

    } else if (s.type === 'roller') {
      ctx.fillStyle = '#38bdf8';
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(sx - 12, sy + 16);
      ctx.lineTo(sx + 12, sy + 16);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = '#94a3b8';
      ctx.beginPath();
      ctx.arc(sx - 6, sy + 20, 3.5, 0, Math.PI * 2);
      ctx.arc(sx + 6, sy + 20, 3.5, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(sx - 16, sy + 25);
      ctx.lineTo(sx + 16, sy + 25);
      ctx.stroke();

      drawGroundHatch(ctx, sx - 16, sx + 16, sy + 25);

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(${s.position}m, sx, sy + 40);

    } else if (s.type === 'fixed') {
      const isLeft = s.position <= L / 2;
      ctx.fillStyle = '#334155';
      ctx.strokeStyle = '#0284c7';
      ctx.lineWidth = 2;

      ctx.beginPath();
      ctx.rect(isLeft ? sx - 14 : sx, beamY - 30, 14, 60);
      ctx.fill();
      ctx.stroke();

      ctx.strokeStyle = '#64748b';
      ctx.lineWidth = 1.5;
      for (let y = beamY - 26; y <= beamY + 26; y += 8) {
        ctx.beginPath();
        if (isLeft) {
          ctx.moveTo(sx - 14, y + 6);
          ctx.lineTo(sx, y - 4);
        } else {
          ctx.moveTo(sx, y + 6);
          ctx.lineTo(sx + 14, y - 4);
        }
        ctx.stroke();
      }

      ctx.fillStyle = '#94a3b8';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(Fixed (m), sx, beamY + 42);
    }
  });

  // 3. Draw Loads
  loadsList.forEach(l => {
    if (l.type === 'point') {
      const lx = toCanvasX(l.position);
      const topY = beamY - beamH / 2 - 45;
      const botY = beamY - beamH / 2;

      ctx.strokeStyle = '#f43f5e';
      ctx.fillStyle = '#f43f5e';
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.moveTo(lx, topY);
      ctx.lineTo(lx, botY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(lx, botY);
      ctx.lineTo(lx - 6, botY - 12);
      ctx.lineTo(lx + 6, botY - 12);
      ctx.closePath();
      ctx.fill();

      ctx.font = 'bold 11px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(${l.magnitude} kN, lx, topY - 6);

    } else if (l.type === 'udl') {
      const x1 = toCanvasX(l.start_pos);
      const x2 = toCanvasX(l.end_pos);
      const udlW = x2 - x1;
      const loadH = 28;
      const topY = beamY - beamH / 2 - loadH;
      const botY = beamY - beamH / 2;

      if (udlW > 2) {
        ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
        ctx.fillRect(x1, topY, udlW, loadH);

        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, topY);
        ctx.lineTo(x2, topY);
        ctx.stroke();

        ctx.fillStyle = '#38bdf8';
        const numArrows = Math.max(2, Math.floor(udlW / 24));
        const step = udlW / numArrows;

        for (let k = 0; k <= numArrows; k++) {
          const ax = x1 + k * step;
          ctx.beginPath();
          ctx.moveTo(ax, topY);
          ctx.lineTo(ax, botY);
          ctx.stroke();

          ctx.beginPath();
          ctx.moveTo(ax, botY);
          ctx.lineTo(ax - 4, botY - 7);
          ctx.lineTo(ax + 4, botY - 7);
          ctx.closePath();
          ctx.fill();
        }

        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillText(w =  kN/m, (x1 + x2) / 2, topY - 6);
      }

    } else if (l.type === 'uvl') {
      const x1 = toCanvasX(l.start_pos);
      const x2 = toCanvasX(l.end_pos);
      const uvlW = x2 - x1;
      const w1 = l.start_magnitude || 0;
      const w2 = l.end_magnitude || 0;
      const maxW = Math.max(Math.abs(w1), Math.abs(w2), 0.1);
      const maxH = 34;

      const h1 = (w1 / maxW) * maxH;
      const h2 = (w2 / maxW) * maxH;

      const botY = beamY - beamH / 2;
      const y1 = botY - h1;
      const y2 = botY - h2;

      if (uvlW > 2) {
        ctx.fillStyle = 'rgba(168, 85, 247, 0.18)';
        ctx.beginPath();
        ctx.moveTo(x1, botY);
        ctx.lineTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.lineTo(x2, botY);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = '#a855f7';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        ctx.fillStyle = '#a855f7';
        ctx.font = 'bold 11px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        ctx.fillText(${w1} →  kN/m, (x1 + x2) / 2, Math.min(y1, y2) - 6);
      }

    } else if (l.type === 'moment') {
      const mx = toCanvasX(l.position);
      const my = beamY;
      const radius = 18;

      ctx.strokeStyle = '#f59e0b';
      ctx.fillStyle = '#f59e0b';
      ctx.lineWidth = 2.5;

      ctx.beginPath();
      ctx.arc(mx, my, radius, -Math.PI * 0.8, Math.PI * 0.7, false);
      ctx.stroke();

      const endAngle = Math.PI * 0.7;
      const tipX = mx + radius * Math.cos(endAngle);
      const tipY = my + radius * Math.sin(endAngle);

      ctx.beginPath();
      ctx.moveTo(tipX, tipY);
      ctx.lineTo(tipX + 8, tipY - 4);
      ctx.lineTo(tipX + 4, tipY + 7);
      ctx.closePath();
      ctx.fill();

      ctx.font = 'bold 11px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(${l.magnitude} kN·m, mx, my - radius - 6);
    }
  });

  // 4. Dimension Line below
  const dimY = beamY + 65;
  ctx.strokeStyle = '#475569';
  ctx.lineWidth = 1;

  ctx.beginPath();
  ctx.moveTo(marginX, dimY);
  ctx.lineTo(marginX + drawW, dimY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(marginX, dimY - 5);
  ctx.lineTo(marginX, dimY + 5);
  ctx.moveTo(marginX + drawW, dimY - 5);
  ctx.lineTo(marginX + drawW, dimY + 5);
  ctx.stroke();

  ctx.fillStyle = '#cbd5e1';
  ctx.font = 'bold 11px JetBrains Mono, monospace';
  ctx.textAlign = 'center';
  ctx.fillText(Total Length L =  m, marginX + drawW / 2, dimY + 16);
}

function drawGroundHatch(ctx, x1, x2, y) {
  ctx.strokeStyle = '#475569';
  ctx.lineWidth = 1;
  for (let hx = x1; hx <= x2; hx += 5) {
    ctx.beginPath();
    ctx.moveTo(hx, y);
    ctx.lineTo(hx - 5, y + 6);
    ctx.stroke();
  }
}

// Main Calculation Trigger
async function calculateBeam() {
  btnCalculate.disabled = true;
  btnCalculate.innerHTML = '<span class="btn-icon">⏳</span> Solving Equations...';

  const payload = {
    beam: {
      length: parseFloat(beamLengthInput.value) || 6.0,
      elastic_modulus: parseFloat(elasticModulusInput.value) || 200.0,
      moment_of_inertia: parseFloat(momentOfInertiaInput.value) || 83.3
    },
    supports: supportsList.map(s => ({
      id: s.id,
      type: s.type,
      position: parseFloat(s.position) || 0.0
    })),
    loads: loadsList.map(l => ({
      id: l.id,
      type: l.type,
      magnitude: parseFloat(l.magnitude) || 0.0,
      position: parseFloat(l.position) || 0.0,
      start_pos: parseFloat(l.start_pos) || 0.0,
      end_pos: parseFloat(l.end_pos) || 0.0,
      start_magnitude: parseFloat(l.start_magnitude) || 0.0,
      end_magnitude: parseFloat(l.end_magnitude) || 0.0
    }))
  };

  try {
    const res = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert(Calculation error: );
      return;
    }

    const result = await res.json();
    renderAnalysisResults(result);

  } catch (err) {
    alert(Network / solver failure: );
  } finally {
    btnCalculate.disabled = false;
    btnCalculate.innerHTML = '<span class="btn-icon">⚡</span> Calculate & Solve Diagrams';
  }
}

// Render Results & Plots
function renderAnalysisResults(res) {
  const maxDef = Math.abs(res.max_deflection_mm);
  document.getElementById('valMaxDeflection').textContent = ${maxDef.toFixed(3)} mm;
  document.getElementById('subMaxDeflection').textContent = t x =  m;

  const absMaxM = Math.max(Math.abs(res.max_moment_kNm), Math.abs(res.min_moment_kNm));
  document.getElementById('valMaxMoment').textContent = ${absMaxM.toFixed(2)} kN·m;
  document.getElementById('subMaxMoment').textContent = Range: [, +];

  const absMaxV = Math.max(Math.abs(res.max_shear_kN), Math.abs(res.min_shear_kN));
  document.getElementById('valMaxShear').textContent = ${absMaxV.toFixed(2)} kN;
  document.getElementById('subMaxShear').textContent = Range: [, +];

  const eq = res.equilibrium;
  const isOk = eq.is_equilibrated;
  document.getElementById('valEquilibrium').innerHTML = isOk
    ? <span style="color: #10b981;">Balanced ✓</span>
    : <span style="color: #f43f5e;">Unbalanced !</span>;
  document.getElementById('subEquilibrium').textContent = ΔFy=kN, ΔM=kNm;

  const reactionsContainer = document.getElementById('reactionsContainer');
  reactionsContainer.innerHTML = '';
  res.reactions.forEach(r => {
    const chip = document.createElement('div');
    chip.className = 'reaction-chip';
    const mStr = Math.abs(r.moment_kNm) > 0.001 ? , M =  kN·m : '';
    chip.innerHTML = <strong> ( @ m):</strong> Ry =  kN;
    reactionsContainer.appendChild(chip);
  });

  const criticalBody = document.getElementById('criticalBody');
  criticalBody.innerHTML = '';
  if (res.critical_points && res.critical_points.length > 0) {
    res.critical_points.forEach(cp => {
      const tr = document.createElement('tr');
      const badgeClass = cp.type.includes('deflection') ? 'badge-success' : (cp.type.includes('moment') ? 'badge' : '');
      tr.innerHTML = 
        <td><span class="badge "></span></td>
        <td><strong> m</strong></td>
        <td><strong> </strong></td>
        <td></td>
      ;
      criticalBody.appendChild(tr);
    });
  } else {
    criticalBody.innerHTML = '<tr><td colspan="4" class="text-center">No critical singularity points detected.</td></tr>';
  }

  renderChart('chartSFD', 'Shear Force V(x)', res.diagrams.x, res.diagrams.shear_force, '#38bdf8', 'kN');
  renderChart('chartBMD', 'Bending Moment M(x)', res.diagrams.x, res.diagrams.bending_moment, '#a855f7', 'kN·m');
  renderChart('chartDeflection', 'Deflection v(x)', res.diagrams.x, res.diagrams.deflection, '#10b981', 'mm');
  renderChart('chartSlope', 'Slope θ(x)', res.diagrams.x, res.diagrams.slope, '#f59e0b', 'mrad');
}

function formatEventName(str) {
  return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function renderChart(canvasId, label, xData, yData, color, unit) {
  const ctx = document.getElementById(canvasId).getContext('2d');

  if (chartInstances[canvasId]) {
    chartInstances[canvasId].destroy();
  }

  const gradient = ctx.createLinearGradient(0, 0, 0, 180);
  gradient.addColorStop(0, hexToRgba(color, 0.35));
  gradient.addColorStop(1, hexToRgba(color, 0.02));

  const points = xData.map((x, i) => ({ x: x, y: yData[i] }));

  chartInstances[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: label,
        data: points,
        borderColor: color,
        borderWidth: 2,
        backgroundColor: gradient,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 400 },
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0e1626',
          titleColor: '#94a3b8',
          bodyColor: '#fff',
          borderColor: '#24324f',
          borderWidth: 1,
          padding: 8,
          callbacks: {
            title: (items) => Span Position x =  m,
            label: (item) => ${label}:  
          }
        }
      },
      scales: {
        x: {
          type: 'linear',
          title: {
            display: true,
            text: 'Beam Span (meters)',
            color: '#64748b',
            font: { size: 10 }
          },
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        },
        y: {
          title: {
            display: true,
            text: ${label} [],
            color: '#64748b',
            font: { size: 10 }
          },
          grid: {
            color: (ctx) => ctx.tick.value === 0 ? 'rgba(255, 255, 255, 0.35)' : 'rgba(255, 255, 255, 0.05)',
            lineWidth: (ctx) => ctx.tick.value === 0 ? 1.5 : 1
          },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        }
      }
    }
  });
}

function hexToRgba(hex, alpha) {
  let c;
  if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
    c = hex.substring(1).split('');
    if (c.length === 3) {
      c = [c[0], c[0], c[1], c[1], c[2], c[2]];
    }
    c = '0x' + c.join('');
    return 
gba(,);
  }
  return hex;
}
