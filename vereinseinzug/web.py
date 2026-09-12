"""
Embedded lightweight web server and UI for SEPA pain.008.001.08 generation.
Runs using Python standard library http.server without heavy frameworks.
"""

import json
import urllib.parse
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any

from .config import ClubConfig
from .parser import parse_csv_content, generate_sample_csv
from .generator import SepaPain008Generator
from .iban import validate_iban, validate_creditor_id, validate_bic, clean_iban, clean_bic
from .logger import logger
from .protocol import generate_audit_protocol

HTML_PAGE = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SEPA pain.008.001.08 Lastschrift-Generator</title>
  <style>
    :root {
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --success: #16a34a;
      --success-bg: #dcfce7;
      --danger: #dc2626;
      --danger-bg: #fee2e2;
      --warning: #d97706;
      --warning-bg: #fef3c7;
      --radius: 10px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 24px 16px; line-height: 1.5; }
    .container { max-width: 1100px; margin: 0 auto; }
    
    header { margin-bottom: 24px; }
    .header-badge { display: inline-block; background: #e0e7ff; color: #4338ca; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; margin-bottom: 8px; }
    h1 { font-size: 26px; font-weight: 800; color: #1e293b; margin-bottom: 4px; }
    p.subtitle { color: var(--text-muted); font-size: 15px; }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 24px; }
    .stat-card { background: var(--card-bg); padding: 16px 20px; border-radius: var(--radius); border: 1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .stat-label { font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .stat-value { font-size: 24px; font-weight: 800; margin-top: 4px; color: #1e293b; }
    .stat-value.valid { color: var(--success); }
    .stat-value.invalid { color: var(--danger); }
    .stat-value.amount { color: var(--primary); }

    .card { background: var(--card-bg); border-radius: var(--radius); border: 1px solid var(--border); padding: 22px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .card-title { font-size: 17px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }
    
    .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }
    .form-group { display: flex; flex-direction: column; }
    label { font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #334155; }
    input, select { padding: 9px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; outline: none; transition: border-color 0.15s; background: #fff; }
    input:focus, select:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }
    .help-text { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

    .dropzone { border: 2px dashed #cbd5e1; border-radius: var(--radius); padding: 32px 20px; text-align: center; background: #f1f5f9; cursor: pointer; transition: all 0.2s; }
    .dropzone.dragover { border-color: var(--primary); background: #eff6ff; }
    .dropzone p { margin: 8px 0; font-size: 14px; color: var(--text-muted); }
    .dropzone-icon { font-size: 32px; color: var(--primary); }

    .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 9px 18px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; transition: background 0.15s, transform 0.05s; }
    .btn:active { transform: translateY(1px); }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-secondary { background: #f1f5f9; color: #334155; border: 1px solid var(--border); }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-success { background: var(--success); color: #fff; }
    .btn-success:hover { background: #15803d; }
    .btn-group { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }

    table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 14px; }
    th { text-align: left; padding: 10px 12px; background: #f8fafc; border-bottom: 2px solid var(--border); color: #475569; font-weight: 600; }
    td { padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
    tr:hover td { background: #f8fafc; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; }
    .badge-success { background: var(--success-bg); color: var(--success); }
    .badge-danger { background: var(--danger-bg); color: var(--danger); }
    .badge-warning { background: var(--warning-bg); color: var(--warning); }
    
    .table-container { max-height: 420px; overflow-y: auto; border: 1px solid var(--border); border-radius: 6px; }
    .error-list { list-style: none; color: var(--danger); font-size: 12px; margin-top: 2px; }
    .warning-list { list-style: none; color: var(--warning); font-size: 12px; margin-top: 2px; }

    .filter-tabs { display: flex; gap: 8px; margin-bottom: 12px; }
    .tab-btn { padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid var(--border); background: #fff; color: var(--text-muted); }
    .tab-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

    .banner { padding: 14px 18px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; display: flex; align-items: center; gap: 12px; }
    .banner-success { background: var(--success-bg); color: #14532d; border: 1px solid #bbf7d0; }
    .banner-danger { background: var(--danger-bg); color: #7f1d1d; border: 1px solid #fecaca; }

    .xml-preview { background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 6px; font-family: monospace; font-size: 12px; max-height: 280px; overflow-y: auto; white-space: pre; margin-top: 14px; }
    
    .hidden { display: none !important; }
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="header-badge">EPC SEPA Standard 2024+ (pain.008.001.08) <span style="opacity: 0.85; font-weight: normal; margin-left: 6px;">v0.2.0</span></div>
    <h1>SEPA-Lastschrift Generator für Vereine</h1>
    <p class="subtitle">Erstellen Sie aus einer Mitglieder-CSV bankenkonforme SEPA-Basislastschriften mit integrierter XSD-Validierung.</p>
  </header>

  <!-- STATS -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-label">Mitglieder geladen</div>
      <div class="stat-value" id="stat-total">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Gültige Lastschriften</div>
      <div class="stat-value valid" id="stat-valid">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Fehlerhafte Datensätze</div>
      <div class="stat-value invalid" id="stat-invalid">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Gesamteinzugssumme</div>
      <div class="stat-value amount" id="stat-amount">0,00 €</div>
    </div>
  </div>

  <!-- 1. VEREINSDATEN -->
  <div class="card">
    <div class="card-title">
      <span>1. Vereinsdaten (Gläubiger)</span>
      <button type="button" class="btn btn-secondary" style="font-size:12px; padding:4px 10px;" id="btn-save-config">Im Browser speichern</button>
    </div>
    <div class="form-grid">
      <div class="form-group">
        <label>Vereinsname (Gläubiger)</label>
        <input type="text" id="cfg-creditor-name" placeholder="z.B. Sportverein Musterstadt e.V.">
      </div>
      <div class="form-group">
        <label>Gläubiger-ID (Creditor Identifier)</label>
        <input type="text" id="cfg-creditor-id" placeholder="z.B. DE98ZZZ09999999999">
        <span class="help-text">Offizielle SEPA-Gläubiger-Identifikationsnummer</span>
      </div>
      <div class="form-group">
        <label>Vereins-IBAN</label>
        <input type="text" id="cfg-creditor-iban" placeholder="DE...">
      </div>
      <div class="form-group">
        <label>Vereins-BIC (optional)</label>
        <input type="text" id="cfg-creditor-bic" placeholder="z.B. BYLADEM1001">
      </div>
      <div class="form-group">
        <label>Einzugsdatum (Fälligkeit)</label>
        <input type="date" id="cfg-collection-date">
      </div>
      <div class="form-group">
        <label>Sequenztyp</label>
        <select id="cfg-sequence-type">
          <option value="RCUR" selected>RCUR (Wiederkehrend / Folgelastschrift - Standard)</option>
          <option value="FRST">FRST (Erstlastschrift)</option>
          <option value="OOFF">OOFF (Einmallastschrift)</option>
          <option value="FNAL">FNAL (Letztlastschrift)</option>
        </select>
      </div>
      <div class="form-group" style="grid-column: span 2;">
        <label>Standard-Verwendungszweck (falls nicht in CSV)</label>
        <input type="text" id="cfg-default-remittance" value="Mitgliedsbeitrag 2026">
      </div>
    </div>
  </div>

  <!-- 2. CSV UPLOAD -->
  <div class="card">
    <div class="card-title">2. Mitglieder-CSV importieren</div>
    <div class="dropzone" id="dropzone" style="position: relative; overflow: hidden; cursor: pointer;">
      <input type="file" id="file-input" accept=".csv,text/csv,text/plain" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; z-index: 10;">
      <div class="dropzone-icon">📁</div>
      <p style="font-weight: 700; color: #1e293b; font-size: 15px;">CSV-Datei hier ablegen oder klicken zum Auswählen</p>
      <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">Unterstützt Spalten wie Name, IBAN, BIC, Betrag in Euro, Mandatsreferenz, Mandatsdatum.</p>
      <button type="button" class="btn btn-primary" style="pointer-events: none; position: relative; z-index: 5;">📄 Datei vom Computer auswählen</button>
      <div id="file-status" class="hidden" style="margin-top: 12px; font-weight: 600; color: var(--primary); font-size: 13px;"></div>
    </div>
    <div class="btn-group">
      <button class="btn btn-secondary" id="btn-download-template">📥 Muster-Vorlage (CSV) herunterladen</button>
      <button class="btn btn-secondary" id="btn-load-sample">✨ Beispieldaten direkt laden</button>
    </div>
  </div>

  <!-- 3. VORSCHAU & PRÜFUNG -->
  <div class="card" id="preview-card" style="display:none;">
    <div class="card-title">
      <span>3. Prüf- und Kontrollansicht</span>
      <div class="filter-tabs">
        <button class="tab-btn active" data-filter="all" id="filter-all">Alle (<span id="count-all">0</span>)</button>
        <button class="tab-btn" data-filter="valid" id="filter-valid">Nur Gültige (<span id="count-valid">0</span>)</button>
        <button class="tab-btn" data-filter="invalid" id="filter-invalid">Fehlerhafte (<span id="count-invalid">0</span>)</button>
      </div>
    </div>

    <div class="table-container">
      <table id="payments-table">
        <thead>
          <tr>
            <th style="width: 70px;">Status</th>
            <th>Name</th>
            <th>IBAN</th>
            <th>BIC</th>
            <th>Betrag</th>
            <th>Mandatsref.</th>
            <th>Mandatsdatum</th>
            <th>Zweck</th>
            <th>Hinweise / Fehler</th>
          </tr>
        </thead>
        <tbody id="payments-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- 4. GENERIEREN -->
  <div class="card" id="generate-card" style="display:none;">
    <div class="card-title">4. SEPA pain.008.001.08 XML Datei erzeugen</div>
    
    <div id="validation-banner" class="banner banner-success hidden">
      <span>✅</span>
      <span id="banner-text">Alle Vorprüfungen erfolgreich. Bereit zur XML-Generierung.</span>
    </div>

    <div class="btn-group">
      <button class="btn btn-primary" id="btn-generate">⚡ pain.008.001.08 XML generieren & prüfen</button>
      <button class="btn btn-success hidden" id="btn-download-xml">💾 XML-Datei herunterladen</button>
      <button class="btn btn-secondary hidden" id="btn-download-protocol">📋 Einzugsprotokoll herunterladen</button>
    </div>

    <div id="xml-container" class="hidden">
      <div style="margin-top: 18px; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:700; font-size:13px;">XML Vorschau (Auszug):</span>
        <span class="badge badge-success">XSD 100% validiert</span>
      </div>
      <div class="xml-preview" id="xml-preview"></div>
    </div>
  </div>
</div>

<script>
let currentPayments = [];
let currentCsvContent = "";
let lastGeneratedXml = "";
let lastGeneratedProtocol = "";

// Auto-fill collection date to +5 days if empty
const dateInput = document.getElementById("cfg-collection-date");
if (!dateInput.value) {
  const d = new Date();
  d.setDate(d.getDate() + 5);
  dateInput.value = d.toISOString().split("T")[0];
}

function applyConfig(cfg) {
  if (!cfg) return;
  if (cfg.creditor_name) document.getElementById("cfg-creditor-name").value = cfg.creditor_name;
  if (cfg.creditor_id) document.getElementById("cfg-creditor-id").value = cfg.creditor_id;
  if (cfg.creditor_iban) document.getElementById("cfg-creditor-iban").value = cfg.creditor_iban;
  if (cfg.creditor_bic) document.getElementById("cfg-creditor-bic").value = cfg.creditor_bic || "";
  if (cfg.collection_date) document.getElementById("cfg-collection-date").value = cfg.collection_date;
  if (cfg.sequence_type) document.getElementById("cfg-sequence-type").value = cfg.sequence_type;
  if (cfg.default_remittance) document.getElementById("cfg-default-remittance").value = cfg.default_remittance;
}

function loadConfig() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has("demo")) {
    applyConfig({
      creditor_name: "Sportverein Musterstadt 1890 e.V.",
      creditor_id: "DE98ZZZ09999999999",
      creditor_iban: "DE89 3704 0044 0532 0130 00",
      creditor_bic: "GENODED1M01",
      collection_date: "2026-10-01",
      sequence_type: "RCUR",
      default_remittance: "Mitgliedsbeitrag 2026"
    });
    return;
  }
  fetch("/api/config")
    .then(r => r.json())
    .then(serverCfg => {
      if (serverCfg && serverCfg.creditor_name) {
        applyConfig(serverCfg);
        localStorage.setItem("sepa_club_config", JSON.stringify(serverCfg));
      } else {
        const saved = localStorage.getItem("sepa_club_config");
        if (saved) {
          try { applyConfig(JSON.parse(saved)); } catch(e) {}
        }
      }
    })
    .catch(() => {
      const saved = localStorage.getItem("sepa_club_config");
      if (saved) {
        try { applyConfig(JSON.parse(saved)); } catch(e) {}
      }
    });
}
loadConfig();

document.getElementById("btn-save-config").addEventListener("click", () => {
  const cfg = getConfig();
  localStorage.setItem("sepa_club_config", JSON.stringify(cfg));
  fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(cfg)
  });
  alert("Vereinsdaten erfolgreich im Browser gespeichert!");
});

function getConfig() {
  return {
    creditor_name: document.getElementById("cfg-creditor-name").value.trim(),
    creditor_id: document.getElementById("cfg-creditor-id").value.trim(),
    creditor_iban: document.getElementById("cfg-creditor-iban").value.trim(),
    creditor_bic: document.getElementById("cfg-creditor-bic").value.trim(),
    collection_date: document.getElementById("cfg-collection-date").value,
    sequence_type: document.getElementById("cfg-sequence-type").value,
    default_remittance: document.getElementById("cfg-default-remittance").value.trim(),
    batch_booking: true
  };
}

// Dropzone handling
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");

fileInput.addEventListener("dragenter", () => dropzone.classList.add("dragover"));
fileInput.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
fileInput.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
fileInput.addEventListener("drop", (e) => {
  dropzone.classList.remove("dragover");
  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
    handleFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", (e) => {
  if (e.target.files && e.target.files.length) {
    handleFile(e.target.files[0]);
  }
});

function handleFile(file) {
  if (!file) return;
  const statusEl = document.getElementById("file-status");
  if (statusEl) {
    statusEl.innerText = "📂 " + file.name + " (" + (file.size < 1024 ? file.size + " B" : Math.round(file.size / 1024) + " KB") + ") geladen";
    statusEl.classList.remove("hidden");
  }

  const reader = new FileReader();
  reader.onload = (ev) => {
    currentCsvContent = ev.target.result;
    parseCsv(currentCsvContent);
  };
  reader.onerror = (ev) => {
    alert("Fehler beim Lesen der Datei: " + (ev.target.error ? ev.target.error.message : "Unbekannt"));
  };
  reader.onloadend = () => {
    try { fileInput.value = ""; } catch(e) {}
  };
  reader.readAsText(file);
}

document.getElementById("btn-load-sample").addEventListener("click", () => {
  fetch("/api/sample-csv").then(r => r.text()).then(csv => {
    currentCsvContent = csv;
    parseCsv(csv);
  });
});

document.getElementById("btn-download-template").addEventListener("click", () => {
  window.location.href = "/api/download-template";
});

function parseCsv(content) {
  const defaultRemittance = document.getElementById("cfg-default-remittance").value;
  fetch("/api/parse-csv", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ csv_content: content, default_remittance: defaultRemittance })
  })
  .then(r => r.json())
  .then(data => {
    const errorMsg = data.error || (data.stats && data.stats.error);
    if (errorMsg) {
      alert("Fehler beim Einlesen der CSV:\\n\\n" + errorMsg);
      return;
    }
    if (!data.stats || data.stats.total_records === undefined) {
      alert("Fehler: Unerwartetes Antwortformat vom Server.");
      return;
    }
    currentPayments = data.payments || [];
    updateStats(data.stats);
    renderTable(currentPayments);
    document.getElementById("preview-card").style.display = "block";
    document.getElementById("generate-card").style.display = "block";
  })
  .catch(err => {
    alert("Verbindungsfehler zum lokalen Server: " + err);
  });
}

function updateStats(stats) {
  document.getElementById("stat-total").innerText = stats.total_records ?? 0;
  document.getElementById("stat-valid").innerText = stats.valid_records ?? 0;
  document.getElementById("stat-invalid").innerText = stats.invalid_records ?? 0;
  document.getElementById("stat-amount").innerText = stats.total_amount_formatted ?? "0,00 €";

  document.getElementById("count-all").innerText = stats.total_records ?? 0;
  document.getElementById("count-valid").innerText = stats.valid_records ?? 0;
  document.getElementById("count-invalid").innerText = stats.invalid_records ?? 0;
}

let activeFilter = "all";
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    renderTable(currentPayments);
  });
});

function renderTable(payments) {
  const tbody = document.getElementById("payments-tbody");
  tbody.innerHTML = "";

  const filtered = payments.filter(p => {
    if (activeFilter === "valid") return p.is_valid;
    if (activeFilter === "invalid") return !p.is_valid;
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:20px; color:var(--text-muted);">Keine Datensätze für diesen Filter</td></tr>';
    return;
  }

  filtered.forEach(p => {
    const tr = document.createElement("tr");
    
    let issuesHtml = "";
    if (p.errors && p.errors.length) {
      issuesHtml += '<ul class="error-list">' + p.errors.map(e => '<li>❌ ' + escapeHtml(e) + '</li>').join("") + '</ul>';
    }
    if (p.warnings && p.warnings.length) {
      issuesHtml += '<ul class="warning-list">' + p.warnings.map(w => '<li>⚠️ ' + escapeHtml(w) + '</li>').join("") + '</ul>';
    }
    if (!issuesHtml) issuesHtml = '<span style="color:var(--text-muted);">-</span>';

    tr.innerHTML = `
      <td>${p.is_valid ? '<span class="badge badge-success">Gültig</span>' : '<span class="badge badge-danger">Fehler</span>'}</td>
      <td><strong>${escapeHtml(p.name)}</strong></td>
      <td style="font-family:monospace;">${escapeHtml(p.iban)}</td>
      <td style="font-family:monospace;">${escapeHtml(p.bic || "-")}</td>
      <td style="font-weight:700;">${escapeHtml(p.amount_formatted)}</td>
      <td style="font-family:monospace;">${escapeHtml(p.mandate_id)}</td>
      <td>${escapeHtml(p.mandate_date)}</td>
      <td>${escapeHtml(p.remittance)}</td>
      <td>${issuesHtml}</td>
    `;
    tbody.appendChild(tr);
  });
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Generate XML
document.getElementById("btn-generate").addEventListener("click", () => {
  const config = getConfig();
  const banner = document.getElementById("validation-banner");

  fetch("/api/generate-xml", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      config: config,
      csv_content: currentCsvContent
    })
  })
  .then(r => r.json())
  .then(res => {
    banner.classList.remove("hidden");
    if (!res.success) {
      banner.className = "banner banner-danger";
      banner.innerHTML = "<span>❌</span><div><strong>Fehler bei der Validierung:</strong><br>" + res.errors.join("<br>") + "</div>";
      document.getElementById("btn-download-xml").classList.add("hidden");
      document.getElementById("btn-download-protocol").classList.add("hidden");
      document.getElementById("xml-container").classList.add("hidden");
    } else {
      lastGeneratedXml = res.xml;
      lastGeneratedProtocol = res.protocol || "";
      banner.className = "banner banner-success";
      banner.innerHTML = `<span>✅</span><div><strong>Erfolgreich generiert und XSD-geprüft!</strong><br>${res.valid_records} Lastschriften im Gesamtwert von ${res.total_amount_formatted} wurden in pain.008.001.08 XML kodiert.</div>`;
      document.getElementById("btn-download-xml").classList.remove("hidden");
      if (lastGeneratedProtocol) {
        document.getElementById("btn-download-protocol").classList.remove("hidden");
      }
      document.getElementById("xml-container").classList.remove("hidden");
      document.getElementById("xml-preview").innerText = res.xml.slice(0, 1500) + (res.xml.length > 1500 ? "\\n\\n... [weitere Zeilen im Download enthalten] ..." : "");
    }
  });
});

document.getElementById("btn-download-xml").addEventListener("click", () => {
  if (!lastGeneratedXml) return;
  const blob = new Blob([lastGeneratedXml], { type: "application/xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const today = new Date().toISOString().split("T")[0];
  a.download = `sepa_lastschrift_pain008_${today}.xml`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

document.getElementById("btn-download-protocol").addEventListener("click", () => {
  if (!lastGeneratedProtocol) return;
  const blob = new Blob([lastGeneratedProtocol], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const today = new Date().toISOString().split("T")[0];
  a.download = `sepa_einzugsprotokoll_${today}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

// URL parameters for demo and automated documentation screenshots
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has("sample")) {
  fetch("/api/sample-csv").then(r => r.text()).then(csv => {
    currentCsvContent = csv;
    parseCsv(csv);
    if (urlParams.has("generate")) {
      setTimeout(() => {
        const genBtn = document.getElementById("btn-generate");
        if (genBtn) genBtn.click();
      }, 500);
    }
  });
}
if (urlParams.has("invalid")) {
  const invalidCsv = "Name;IBAN;Beitrag in Euro;Mandatsreferenz;Mandatsdatum\\nMax Mustermann;DE89370400440532013000;60,00;M-00101;2022-03-15\\nSabine Fehlerhaft;DE1234567890;25,00;;";
  currentCsvContent = invalidCsv;
  parseCsv(invalidCsv);
}
</script>
</body>
</html>
"""


class SepaHttpHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP access logging to keep console clean
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))

        elif path == "/api/sample-csv":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.end_headers()
            self.wfile.write(generate_sample_csv().encode("utf-8"))

        elif path == "/api/download-template":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=mitglieder_vorlage.csv")
            self.end_headers()
            self.wfile.write(generate_sample_csv().encode("utf-8-sig"))

        elif path == "/api/config":
            cfg_file = Path("config.json")
            if cfg_file.is_file():
                try:
                    cfg = ClubConfig.load_from_file(cfg_file)
                    data = cfg.to_dict()
                except Exception:
                    data = {}
            else:
                data = {}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        if path == "/api/parse-csv":
            try:
                data = json.loads(body.decode("utf-8"))
                csv_content = data.get("csv_content", "")
                default_rem = data.get("default_remittance", "Mitgliedsbeitrag")
                payments, stats = parse_csv_content(csv_content, default_remittance=default_rem)
                if "error" in stats:
                    logger.warning("Web API: CSV-Verarbeitung fehlgeschlagen: %s", stats["error"])
                    self.send_json(200, {"error": stats["error"], "payments": [], "stats": stats})
                    return
                logger.info(
                    "Web API: CSV verarbeitet: %d Zeilen (%d gueltig, %d ungueltig, Summe: %s)",
                    stats.get("total_records", 0),
                    stats.get("valid_records", 0),
                    stats.get("invalid_records", 0),
                    stats.get("total_amount_formatted", "0,00"),
                )
                res = {
                    "payments": [p.to_dict() for p in payments],
                    "stats": stats
                }
                self.send_json(200, res)
            except Exception as e:
                logger.error("Web API: Fehler bei /api/parse-csv: %s", str(e))
                self.send_json(400, {"error": str(e)})

        elif path == "/api/config":
            try:
                data = json.loads(body.decode("utf-8"))
                cfg = ClubConfig.from_dict(data)
                cfg.save_to_file(Path("config.json"))
                self.send_json(200, {"success": True})
            except Exception as e:
                self.send_json(400, {"error": str(e)})

        elif path == "/api/generate-xml":
            try:
                data = json.loads(body.decode("utf-8"))
                cfg_data = data.get("config", {})
                csv_content = data.get("csv_content", "")
                config = ClubConfig.from_dict(cfg_data)

                # Validate config
                cfg_errors = config.validate()
                if cfg_errors:
                    logger.error("Web API: Configuration error: %s", "; ".join(cfg_errors))
                    self.send_json(200, {"success": False, "errors": cfg_errors})
                    return

                payments, stats = parse_csv_content(csv_content, default_remittance=config.default_remittance)
                if not payments:
                    self.send_json(200, {"success": False, "errors": ["Keine Zahlungsdaten gefunden."]})
                    return

                valid_payments = [p for p in payments if p.is_valid]
                if not valid_payments:
                    self.send_json(200, {"success": False, "errors": ["Keine gültigen Zahlungssätze vorhanden. Bitte IBAN und Pflichtfelder prüfen."]})
                    return

                logger.info("Web API: Generating XML for %d payments (sum: %s)...",
                            len(valid_payments), stats.get("total_amount_formatted", "0,00"))
                generator = SepaPain008Generator(config)
                xml_str = generator.generate_xml(valid_payments)

                # Validate against official XSD schema
                is_valid, xsd_errors = generator.validate_xml_schema(xml_str)
                if not is_valid:
                    logger.error("Web API: XSD schema validation failed: %s", "; ".join(xsd_errors))
                    self.send_json(200, {"success": False, "errors": [f"XSD Schema-Fehler: {e}" for e in xsd_errors]})
                    return

                logger.info("Web API: XML generation and XSD schema validation successful.")

                # Generate audit protocol
                protocol_str = generate_audit_protocol(
                    config, payments, stats,
                    xml_filename=f"sepa_lastschrift_pain008_{datetime.now().strftime('%Y%m%d')}.xml"
                )

                self.send_json(200, {
                    "success": True,
                    "xml": xml_str,
                    "protocol": protocol_str,
                    "valid_records": len(valid_payments),
                    "total_amount_formatted": stats.get("total_amount_formatted", "0,00 €"),
                })
            except Exception as e:
                logger.error("Web API: Exception during XML generation: %s", str(e))
                self.send_json(200, {"success": False, "errors": [str(e)]})

        else:
            self.send_response(404)
            self.end_headers()

    def send_json(self, status: int, data: Dict[str, Any]):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


def run_web_server(port: int = 8080, open_browser: bool = True):
    """Start local web server and optionally open the browser."""
    import webbrowser
    server_address = ("127.0.0.1", port)
    
    # Try specified port, or try fallback ports
    for p in range(port, port + 10):
        try:
            httpd = HTTPServer(("127.0.0.1", p), SepaHttpHandler)
            url = f"http://127.0.0.1:{p}"
            print(f"===============================================================")
            print(f" SEPA Lastschrift Web-UI gestartet!")
            print(f" URL: {url}")
            print(f" Drücken Sie Ctrl+C im Terminal zum Beenden.")
            print(f"===============================================================")
            logger.info("Web-Server gestartet auf %s", url)
            if open_browser:
                webbrowser.open(url)
            httpd.serve_forever()
            break
        except OSError:
            continue
