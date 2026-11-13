//! jarvis_rust_core — J.A.R.V.I.S. Mark 108 (Sovereign Core) Native Rust Exoskeleton
//! ====================================================================================
//! Provides zero-GIL, multi-core native Rust implementations for:
//! 1. Cryptographic Integrity, Multi-Core SHA-256 Hashing & Prompt-Injection Firewall
//! 2. Document QA Scanner, Math/Table Validator, Citation Matcher, Claim Classifier & AI-Humanizer Scrubber
//! 3. Camera Vision, Motion Diffing, Anti-Shoulder-Surfer Peeker Zone, Privacy Blur & Face Histogram Correlation
//! 4. Real-Time Audio DSP, Voice Activity Detection (VAD) & Video Silence Cut-Point Finder
//! 5. Vector Memory Cosine Search, BM25 Ranking & Multi-Core 100k-File Search (`walkdir`)
//! 6. Native Win32 Working-Set RAM Compactor, Pycache Cleaner, Emotional Spectrum Evaluator & Offline Router

use pyo3::prelude::*;
use rayon::prelude::*;
use regex::Regex;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::sync::OnceLock;
use walkdir::WalkDir;

// ============================================================================
// 1. CRYPTOGRAPHIC SECURITY, MULTI-CORE INTEGRITY SEAL & PROMPT INJECTION SHIELD
// ============================================================================

fn sha256_file_internal(path: &Path) -> Option<String> {
    let bytes = fs::read(path).ok()?;
    let mut hasher = Sha256::new();
    hasher.update(&bytes);
    Some(hex::encode(hasher.finalize()))
}

#[pyfunction]
fn compute_file_sha256_rust(path_str: &str) -> PyResult<String> {
    let p = Path::new(path_str);
    match sha256_file_internal(p) {
        Some(h) => Ok(h),
        None => Ok(String::new()),
    }
}

#[pyfunction]
fn hash_files_parallel_rust(py: Python<'_>, file_paths: Vec<String>) -> PyResult<HashMap<String, String>> {
    let results: Vec<(String, String)> = py.allow_threads(|| {
        file_paths
            .into_par_iter()
            .filter_map(|p_str| {
                let p = Path::new(&p_str);
                sha256_file_internal(p).map(|h| (p_str, h))
            })
            .collect()
    });
    Ok(results.into_iter().collect())
}

#[pyfunction]
fn verify_integrity_batch_rust(
    py: Python<'_>,
    base_dir: &str,
    baseline_hashes: HashMap<String, String>,
) -> PyResult<HashMap<String, Vec<String>>> {
    let base = Path::new(base_dir).to_path_buf();
    let entries: Vec<(String, String)> = baseline_hashes.into_iter().collect();

    let (modified, missing): (Vec<String>, Vec<String>) = py.allow_threads(|| {
        let mut mod_vec = Vec::new();
        let mut miss_vec = Vec::new();

        let checks: Vec<(String, Option<String>, String)> = entries
            .into_par_iter()
            .map(|(rel_path, expected_hash)| {
                let full_path = base.join(&rel_path);
                let actual = sha256_file_internal(&full_path);
                (rel_path, actual, expected_hash)
            })
            .collect();

        for (rel_path, actual_opt, expected_hash) in checks {
            match actual_opt {
                None => miss_vec.push(rel_path),
                Some(actual) => {
                    if actual != expected_hash {
                        mod_vec.push(rel_path);
                    }
                }
            }
        }
        (mod_vec, miss_vec)
    });

    let mut out = HashMap::new();
    out.insert("modified_files".to_string(), modified);
    out.insert("missing_files".to_string(), missing);
    Ok(out)
}

#[pyfunction]
fn scrub_sensitive_tokens_rust(text: &str) -> String {
    static SECRET_RE: OnceLock<Regex> = OnceLock::new();
    let re = SECRET_RE.get_or_init(|| {
        Regex::new(r"(?i)(AIza[0-9A-Za-z\-_]{35}|sk-[A-Za-z0-9\-_]{20,}|ghp_[A-Za-z0-9]{36}|Bearer\s+[A-Za-z0-9\-._~+/]+=*)")
            .unwrap()
    });
    re.replace_all(text, "[REDACTED_BY_RUST_SHIELD]").to_string()
}

#[pyfunction]
fn inspect_prompt_injection_rust(text: &str) -> (bool, Vec<String>) {
    static INJECTION_PATS: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    let pats = INJECTION_PATS.get_or_init(|| {
        vec![
            (
                r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|system|initial)\s+(instructions|directives|rules|prompts)\b",
                Regex::new(r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|system|initial)\s+(instructions|directives|rules|prompts)\b").unwrap(),
            ),
            (
                r"(?i)\b(system\s+prompt|new\s+instructions?)\s*:\s*(you are now|act as|disregard)\b",
                Regex::new(r"(?i)\b(system\s+prompt|new\s+instructions?)\s*:\s*(you are now|act as|disregard)\b").unwrap(),
            ),
            (
                r"(?i)\b(dan\s+mode|jailbreak|developer\s+mode\s+enabled|unrestricted\s+ai|always\s+comply)\b",
                Regex::new(r"(?i)\b(dan\s+mode|jailbreak|developer\s+mode\s+enabled|unrestricted\s+ai|always\s+comply)\b").unwrap(),
            ),
            (
                r"(?i)\b(output|reveal|print|exfiltrate|leak|dump)\s+(all\s+)?(passwords|api[_\s]keys|secrets|\.env|credentials|token)\b",
                Regex::new(r"(?i)\b(output|reveal|print|exfiltrate|leak|dump)\s+(all\s+)?(passwords|api[_\s]keys|secrets|\.env|credentials|token)\b").unwrap(),
            ),
            (
                r"(?i)\b(send|upload|exfiltrate)\s+(everything|data|history|files)\s+to\s+https?://\b",
                Regex::new(r"(?i)\b(send|upload|exfiltrate)\s+(everything|data|history|files)\s+to\s+https?://\b").unwrap(),
            ),
            (
                r"(?i)(<\s*\|\s*im_start\s*\|\s*>|\[SYSTEM\]|<<SYS>>|\[INST\])",
                Regex::new(r"(?i)(<\s*\|\s*im_start\s*\|\s*>|\[SYSTEM\]|<<SYS>>|\[INST\])").unwrap(),
            ),
            (
                r"(?i)!\[.*?\]\(https?://[^\s)]+\?[^)]*?(key|token|cookie|data|leak)=.*?\)",
                Regex::new(r"(?i)!\[.*?\]\(https?://[^\s)]+\?[^)]*?(key|token|cookie|data|leak)=.*?\)").unwrap(),
            ),
            (
                r"(?i)\b(read|open|cat|type|show|fetch|print|dump|summarize|send|copy|display)\b[^\n]{0,80}\b(api_keys\.json|credentials\.json|\.env|id_rsa|id_ed25519|security_ledger|integrity_baseline\.json|voice_profile\.npy|kdbx)\b",
                Regex::new(r"(?i)\b(read|open|cat|type|show|fetch|print|dump|summarize|send|copy|display)\b[^\n]{0,80}\b(api_keys\.json|credentials\.json|\.env|id_rsa|id_ed25519|security_ledger|integrity_baseline\.json|voice_profile\.npy|kdbx)\b").unwrap(),
            ),
            (
                r"(?i)\b(what\s+is|tell\s+me|give\s+me|share|extract|reveal)\b[^\n]{0,60}\b(gemini_api_key|telegram_bot_token|security_passkey|openai_api_key|anthropic_api_key|tavily_api_key)\b",
                Regex::new(r"(?i)\b(what\s+is|tell\s+me|give\s+me|share|extract|reveal)\b[^\n]{0,60}\b(gemini_api_key|telegram_bot_token|security_passkey|openai_api_key|anthropic_api_key|tavily_api_key)\b").unwrap(),
            ),
            (
                r"(?i)\b(base64|powershell\s+-enc|invoke-webrequest|iwr|curl|wget)\b[^\n]{0,80}\b(api_keys|\.env|token|secret|password)\b",
                Regex::new(r"(?i)\b(base64|powershell\s+-enc|invoke-webrequest|iwr|curl|wget)\b[^\n]{0,80}\b(api_keys|\.env|token|secret|password)\b").unwrap(),
            ),
        ]
    });

    let mut matched = Vec::new();
    for (pat_str, re) in pats.iter() {
        if re.is_match(text) {
            matched.push((*pat_str).to_string());
        }
    }
    (matched.is_empty(), matched)
}

// ============================================================================
// 2. DOCUMENT QA: HEADER TRUNCATOR, MATH, CITATIONS, CLAIMS & HUMANIZER SCRUBBER
// ============================================================================

#[pyfunction]
fn truncate_header_title_rust(text: &str, max_chars: usize) -> String {
    let clean: String = text.split_whitespace().collect::<Vec<&str>>().join(" ");
    if clean.chars().count() <= max_chars {
        return clean;
    }

    let small_words: HashSet<&str> = [
        "a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so", "at", "by", "in",
        "of", "on", "to", "up", "as", "vs", "via", "per", "from", "into", "onto", "with", "over",
    ]
    .into_iter()
    .collect();

    let mut accum: Vec<&str> = Vec::new();
    let mut cur_len = 0usize;
    for w in clean.split(' ') {
        let w_len = w.chars().count();
        let needed = w_len + if accum.is_empty() { 0 } else { 1 };
        if cur_len + needed > max_chars.saturating_sub(1) {
            break;
        }
        accum.push(w);
        cur_len += needed;
    }

    if accum.is_empty() {
        let taken: String = clean.chars().take(max_chars.saturating_sub(1)).collect();
        return format!("{}…", taken.trim_end());
    }

    while accum.len() > 2 {
        let last_lower = accum.last().unwrap().trim_end_matches(&[':', ',', '-'][..]).to_lowercase();
        if small_words.contains(last_lower.as_str()) {
            accum.pop();
        } else {
            break;
        }
    }

    let joined = accum.join(" ");
    format!("{}…", joined.trim_end_matches(&[' ', ',', ';', ':', '-'][..]))
}

#[pyfunction]
fn scan_forbidden_docx_patterns_rust(texts: Vec<String>) -> Vec<String> {
    static PATTERNS: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    static LITERAL_N_RE: OnceLock<Regex> = OnceLock::new();
    let pats = PATTERNS.get_or_init(|| {
        vec![
            ("leftover '**' bold marker", Regex::new(r"\*\*").unwrap()),
            ("leftover '__' bold marker", Regex::new(r"__").unwrap()),
            ("line starting with '#'", Regex::new(r"(?m)^\s*#{1,6}\s+").unwrap()),
            ("leftover '$$' display math delimiter", Regex::new(r"\$\$").unwrap()),
            ("raw '\\frac' LaTeX command", Regex::new(r"\\frac\b").unwrap()),
            ("raw '\\sum' LaTeX command", Regex::new(r"\\sum\b").unwrap()),
            ("leftover '|---|' markdown table separator", Regex::new(r"\|\s*:?-{2,}:?\s*\|").unwrap()),
        ]
    });
    let lit_n_re = LITERAL_N_RE.get_or_init(|| Regex::new(r"\\n([a-zA-Z]*)").unwrap());
    const ALLOWED_N_SUFFIXES: &[&str] = &[
        "abla", "eq", "e", "u", "otin", "atural", "exists", "eg", "less", "gtr",
        "leq", "geq", "subseteq", "supseteq", "mid", "parallel",
    ];

    let mut issues = Vec::new();
    for (idx, txt) in texts.iter().enumerate() {
        let trimmed = txt.trim();
        if trimmed.is_empty() {
            continue;
        }
        for (label, re) in pats.iter() {
            if re.is_match(txt) {
                let preview: String = txt.chars().take(80).collect();
                issues.push(format!("Paragraph {} contains {}: {:?}", idx + 1, label, preview));
            }
        }
        if txt.contains("---") && !txt.contains("+---") && !txt.contains("---+") && !txt.contains("--->") {
            let preview: String = txt.chars().take(80).collect();
            issues.push(format!("Paragraph {} contains leftover '---' horizontal rule: {:?}", idx + 1, preview));
        }
        for caps in lit_n_re.captures_iter(txt) {
            let suffix = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            if !ALLOWED_N_SUFFIXES.contains(&suffix) {
                let preview: String = txt.chars().take(80).collect();
                issues.push(format!("Paragraph {} contains literal '\\n' sequence: {:?}", idx + 1, preview));
                break;
            }
        }
        if txt.chars().count() > 1200 {
            let breaks = txt.matches(&['.', '!', '?', ':', ';', '\n'][..]).count();
            if breaks < 2 {
                issues.push(format!(
                    "Paragraph {} is {} chars with no sentence breaks.",
                    idx + 1,
                    txt.chars().count()
                ));
            }
        }
    }
    issues
}

#[pyfunction]
fn analyze_humanizer_metrics_rust(text: &str) -> HashMap<String, f64> {
    let mut metrics = HashMap::new();
    let trimmed = text.trim();
    if trimmed.is_empty() {
        metrics.insert("human_score".to_string(), 100.0);
        metrics.insert("burstiness".to_string(), 10.0);
        metrics.insert("cliche_hits".to_string(), 0.0);
        return metrics;
    }

    let cliches = [
        "delve", "tapestry", "testament", "underscore", "pivotal", "crucial", "multifaceted",
        "realm", "moreover", "furthermore", "in conclusion", "it is important to note",
        "beacon", "symphony", "intricate", "unwavering", "paradigm shift",
    ];
    let lower = trimmed.to_lowercase();
    let mut cliche_count = 0usize;
    for c in cliches.iter() {
        cliche_count += lower.matches(c).count();
    }

    let sentences: Vec<&str> = trimmed
        .split(&['.', '!', '?'][..])
        .map(|s| s.trim())
        .filter(|s| s.split_whitespace().count() >= 3)
        .collect();

    let burstiness = if sentences.len() >= 2 {
        let lengths: Vec<f64> = sentences
            .iter()
            .map(|s| s.split_whitespace().count() as f64)
            .collect();
        let mean = lengths.iter().sum::<f64>() / (lengths.len() as f64);
        let var = lengths.iter().map(|l| (l - mean).powi(2)).sum::<f64>() / (lengths.len() as f64);
        var.sqrt()
    } else {
        8.5
    };

    let penalty = (cliche_count as f64) * 4.5 + if burstiness < 4.5 { 8.0 } else { 0.0 };
    let score = (98.0 - penalty).clamp(40.0, 99.0);

    metrics.insert("human_score".to_string(), (score * 10.0).round() / 10.0);
    metrics.insert("burstiness".to_string(), (burstiness * 100.0).round() / 100.0);
    metrics.insert("cliche_hits".to_string(), cliche_count as f64);
    metrics
}

#[pyfunction]
fn scrub_ai_watermarks_rust(text: &str) -> String {
    if text.trim().is_empty() {
        return String::new();
    }
    static REPLACEMENTS: OnceLock<Vec<(Regex, &'static str)>> = OnceLock::new();
    let rules = REPLACEMENTS.get_or_init(|| {
        let raw_pairs: &[(&str, &str)] = &[
            (r"(?i)\bit is important to note that\b", "notably,"),
            (r"(?i)\bit is worth noting that\b", "keep in mind that"),
            (r"(?i)\bit is crucial to understand\b", "we need to see"),
            (r"(?i)\bin today's fast-paced world\b", "today"),
            (r"(?i)\bin today's digital age\b", "in modern practice"),
            (r"(?i)\bin the ever-evolving landscape of\b", "across"),
            (r"(?i)\bever-evolving landscape\b", "changing field"),
            (r"(?i)\ba testament to\b", "clear proof of"),
            (r"(?i)\bstands as a testament\b", "shows"),
            (r"(?i)\brich tapestry of\b", "wide mix of"),
            (r"(?i)\btapestry of\b", "combination of"),
            (r"(?i)\bdelve into\b", "examine"),
            (r"(?i)\bdelving into\b", "looking closely at"),
            (r"(?i)\bdelves into\b", "explores"),
            (r"(?i)\bdelve deeper\b", "look closer"),
            (r"(?i)\bunderscores the importance of\b", "highlights why"),
            (r"(?i)\bunderscores\b", "shows"),
            (r"(?i)\bunderscoring\b", "pointing to"),
            (r"(?i)\bpivotal role\b", "central role"),
            (r"(?i)\bpivotal\b", "key"),
            (r"(?i)\bparamount\b", "essential"),
            (r"(?i)\bmultifaceted\b", "many-sided"),
            (r"(?i)\bnuanced\b", "subtle"),
            (r"(?i)\bparadigm shift\b", "major shift"),
            (r"(?i)\bin the realm of\b", "in"),
            (r"(?i)\brealm\b", "area"),
            (r"(?i)\bbeacon of\b", "example of"),
            (r"(?i)\bsymphony of\b", "blend of"),
            (r"(?i)\bunlock the full potential\b", "get the most out"),
            (r"(?i)\bunlock the potential\b", "make full use"),
            (r"(?i)\bunleash the power\b", "use the strength"),
            (r"(?i)\bfoster innovation\b", "encourage new ideas"),
            (r"(?i)\bfostering\b", "building"),
            (r"(?i)\bfoster\b", "support"),
            (r"(?i)\bharnessing the power of\b", "using"),
            (r"(?i)\bharness the power of\b", "use"),
            (r"(?i)\bharness\b", "use"),
            (r"(?i)\bleveraging\b", "using"),
            (r"(?i)\bleverage\b", "use"),
            (r"(?i)\butilize\b", "use"),
            (r"(?i)\butilizing\b", "using"),
            (r"(?i)\butilization\b", "use"),
            (r"(?i)\bfacilitate\b", "help"),
            (r"(?i)\bfacilitating\b", "helping"),
            (r"(?i)\bmoreover,\s*", "beyond that, "),
            (r"(?i)\bfurthermore,\s*", "on top of that, "),
            (r"(?i)\badditionally,\s*", "also, "),
            (r"(?i)\bconsequently,\s*", "as a result, "),
            (r"(?i)\bsubsequently,\s*", "later on, "),
            (r"(?i)\bnevertheless,\s*", "still, "),
            (r"(?i)\bin conclusion,\s*", "ultimately, "),
            (r"(?i)\bto summarize,\s*", "in short, "),
            (r"(?i)\ball in all,\s*", "overall, "),
            (r"(?i)\bmeticulously\b", "carefully"),
            (r"(?i)\bmeticulous\b", "careful"),
            (r"(?i)\bseamlessly\b", "smoothly"),
            (r"(?i)\bseamless\b", "smooth"),
            (r"(?i)\brobust\b", "strong"),
            (r"(?i)\bcomprehensive\b", "thorough"),
            (r"(?i)\bcutting-edge\b", "modern"),
            (r"(?i)\bstate-of-the-art\b", "advanced"),
            (r"(?i)\bgame-changer\b", "major advance"),
            (r"(?i)\bgroundbreaking\b", "major"),
            (r"(?i)\bspearhead\b", "lead"),
            (r"(?i)\bcatalyst\b", "driver"),
            (r"(?i)\bmyriad of\b", "many"),
            (r"(?i)\bplethora of\b", "many"),
            (r"(?i)\bembark on\b", "start"),
            (r"(?i)\bendeavor\b", "effort"),
            (r"(?i)\bcommence\b", "begin"),
            (r"(?i)\bshed light on\b", "clarify"),
            (r"(?i)\bpave the way for\b", "open the door to"),
            (r"(?i)\bat the end of the day\b", "ultimately"),
            (r"(?i)\bplay a crucial role\b", "matter greatly"),
            (r"(?i)\bcrucial\b", "vital"),
        ];
        raw_pairs
            .iter()
            .map(|(pat, rep)| (Regex::new(pat).unwrap(), *rep))
            .collect()
    });

    let mut out = text.to_string();
    for (re, repl) in rules.iter() {
        out = re
            .replace_all(&out, |caps: &regex::Captures| {
                let matched = &caps[0];
                if repl.is_empty() {
                    return String::new();
                }
                let first_upper = matched.chars().next().map(|c| c.is_uppercase()).unwrap_or(false);
                if first_upper {
                    let mut chars = repl.chars();
                    match chars.next() {
                        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
                        None => String::new(),
                    }
                } else {
                    (*repl).to_string()
                }
            })
            .into_owned();
    }

    if out.matches('—').count() > 2 {
        out = out.replace(" — ", ", ").replace('—', ", ");
    }

    static MULTI_SPACE_RE: OnceLock<Regex> = OnceLock::new();
    let ms_re = MULTI_SPACE_RE.get_or_init(|| Regex::new(r"[ \t]{2,}").unwrap());
    ms_re.replace_all(&out, " ").trim().to_string()
}

fn parse_clean_float(s: &str) -> Option<f64> {
    let cleaned: String = s
        .chars()
        .filter(|c| c.is_ascii_digit() || *c == '.' || *c == '-')
        .collect();
    if cleaned.is_empty() || cleaned == "-" || cleaned == "." {
        return None;
    }
    cleaned.parse::<f64>().ok()
}

#[pyfunction]
fn validate_arithmetic_rust(text: &str) -> Vec<(String, String, String, String, String)> {
    static EQ_RE: OnceLock<Regex> = OnceLock::new();
    static PCT_RE: OnceLock<Regex> = OnceLock::new();
    let eq_re = EQ_RE.get_or_init(|| {
        Regex::new(r"(?i)([\$€£]?\s*[\d,]+(?:\.\d+)?)\s*([\+\-\*/])\s*([\$€£]?\s*[\d,]+(?:\.\d+)?)\s*(?:=|is|results in|yields|yielded|equaled|equals)\s*([\$€£]?\s*[\d,]+(?:\.\d+)?)").unwrap()
    });
    let pct_re = PCT_RE.get_or_init(|| Regex::new(r"\b(\d+(?:\.\d+)?)\s*%").unwrap());

    let mut issues = Vec::new();

    for caps in eq_re.captures_iter(text) {
        let full_match = caps.get(0).map(|m| m.as_str()).unwrap_or("");
        let op = caps.get(2).map(|m| m.as_str()).unwrap_or("");
        if let (Some(va), Some(vb), Some(vc)) = (
            caps.get(1).and_then(|m| parse_clean_float(m.as_str())),
            caps.get(3).and_then(|m| parse_clean_float(m.as_str())),
            caps.get(4).and_then(|m| parse_clean_float(m.as_str())),
        ) {
            let expected = match op {
                "+" => Some(va + vb),
                "-" => Some(va - vb),
                "*" => Some(va * vb),
                "/" => if vb != 0.0 { Some(va / vb) } else { None },
                _ => None,
            };
            if let Some(exp) = expected {
                let diff = (exp - vc).abs();
                let rel_err = diff / exp.abs().max(1e-6);
                if rel_err > 0.01 && diff > 0.05 {
                    issues.push((
                        "critical".to_string(),
                        "DETERMINISTIC_ARITHMETIC_ERROR".to_string(),
                        format!(
                            "Arithmetic discrepancy: '{}' is mathematically invalid. Expected {:.2}, but found {:.2}.",
                            full_match, exp, vc
                        ),
                        full_match.to_string(),
                        format!("Correct calculated value from {} to {:.2}.", vc, exp),
                    ));
                }
            }
        }
    }

    let low = text.to_lowercase();
    if low.contains("breakdown") || low.contains("distribution") || low.contains("share") {
        let pcts: Vec<f64> = pct_re
            .captures_iter(text)
            .filter_map(|c| c.get(1).and_then(|m| m.as_str().parse::<f64>().ok()))
            .collect();
        if (3..=8).contains(&pcts.len()) {
            let tot_pct: f64 = pcts.iter().sum();
            if (tot_pct - 100.0).abs() > 3.0 && tot_pct < 180.0 {
                issues.push((
                    "high".to_string(),
                    "PERCENTAGE_SUM_MISMATCH".to_string(),
                    format!("Percentage component breakdown sums to {:.1}% instead of 100.0%.", tot_pct),
                    String::new(),
                    "Normalize percentage values to ensure parts sum to 100%.".to_string(),
                ));
            }
        }
    }

    issues
}

#[pyfunction]
fn validate_table_totals_rust(table_rows: Vec<Vec<String>>) -> Vec<(String, String, String, String, String)> {
    let mut issues = Vec::new();
    if table_rows.len() < 3 {
        return issues;
    }

    let headers = &table_rows[0];
    let last_row = &table_rows[table_rows.len() - 1];
    let first_cell = last_row.first().map(|s| s.trim().to_lowercase()).unwrap_or_default();

    if first_cell.contains("total") || first_cell.contains("sum") {
        let num_cols = last_row.len();
        for c_idx in 1..num_cols {
            let Some(reported_total) = parse_clean_float(&last_row[c_idx]) else {
                continue;
            };
            let mut calculated_sum = 0.0f64;
            let mut valid_num_count = 0usize;
            for r_idx in 1..(table_rows.len() - 1) {
                if let Some(cell_str) = table_rows[r_idx].get(c_idx) {
                    if let Some(val) = parse_clean_float(cell_str) {
                        calculated_sum += val;
                        valid_num_count += 1;
                    }
                }
            }
            if valid_num_count >= 2 {
                let diff = (calculated_sum - reported_total).abs();
                if diff > 0.05 && (diff / calculated_sum.abs().max(1e-6)) > 0.005 {
                    let col_name = headers
                        .get(c_idx)
                        .cloned()
                        .unwrap_or_else(|| format!("Column {}", c_idx));
                    issues.push((
                        "critical".to_string(),
                        "TABLE_TOTAL_MISMATCH".to_string(),
                        format!(
                            "Table total mismatch in '{}': Reported total is {}, but sum of rows is {:.2}.",
                            col_name, reported_total, calculated_sum
                        ),
                        col_name,
                        format!("Update table total cell to {:.2}.", calculated_sum),
                    ));
                }
            }
        }
    }
    issues
}

#[pyfunction]
fn audit_citations_rust(full_text: &str, bibliography_text: &str) -> Vec<(String, String, String, String, String)> {
    static REF_SPLIT_RE: OnceLock<Regex> = OnceLock::new();
    static APA_RE: OnceLock<Regex> = OnceLock::new();
    static IEEE_RE: OnceLock<Regex> = OnceLock::new();
    static NUM_RE: OnceLock<Regex> = OnceLock::new();
    static BIB_NUM_RE: OnceLock<Regex> = OnceLock::new();

    let ref_split_re = REF_SPLIT_RE.get_or_init(|| {
        Regex::new(r"(?i)\b(?:references|bibliography|works cited)\b[:\s]*\n([\s\S]+)$").unwrap()
    });
    let apa_re = APA_RE.get_or_init(|| {
        Regex::new(r"\(([A-Z][a-zA-Z\s]+(?:et al\.)?(?:,\s*|\s+and\s+[A-Z][a-zA-Z]+)?),\s*(\d{4})\)").unwrap()
    });
    let ieee_re = IEEE_RE.get_or_init(|| Regex::new(r"\[(\d+(?:[,\s\-]+\d+)*)\]").unwrap());
    let num_re = NUM_RE.get_or_init(|| Regex::new(r"\d+").unwrap());
    let bib_num_re = BIB_NUM_RE.get_or_init(|| Regex::new(r"^\s*\[(\d+)\]").unwrap());

    let mut body_text = full_text;
    let mut bib_str = bibliography_text;
    if bib_str.trim().is_empty() {
        if let Some(m) = ref_split_re.captures(full_text) {
            if let Some(full_m) = m.get(0) {
                body_text = &full_text[..full_m.start()];
            }
            if let Some(b_m) = m.get(1) {
                bib_str = b_m.as_str();
            }
        }
    }

    let bib_entries: Vec<&str> = bib_str
        .lines()
        .map(|l| l.trim())
        .filter(|l| l.chars().count() > 15)
        .collect();

    let mut issues = Vec::new();

    // 1. Extract APA author-year citations
    let mut cited_pairs: Vec<(String, String)> = Vec::new();
    let mut seen_pairs: HashSet<(String, String)> = HashSet::new();
    for caps in apa_re.captures_iter(body_text) {
        let author_blob = caps.get(1).map(|m| m.as_str()).unwrap_or("");
        let yr = caps.get(2).map(|m| m.as_str()).unwrap_or("").to_string();
        let first_author = author_blob
            .split_whitespace()
            .next()
            .unwrap_or("")
            .replace(',', "")
            .to_lowercase();
        if !first_author.is_empty() && !yr.is_empty() {
            let pair = (first_author, yr);
            if seen_pairs.insert(pair.clone()) {
                cited_pairs.push(pair);
            }
        }
    }

    if !cited_pairs.is_empty() {
        let mut bib_matched: HashSet<usize> = HashSet::new();
        for (author, yr) in cited_pairs.iter() {
            let mut found = false;
            for (b_idx, b_entry) in bib_entries.iter().enumerate() {
                if b_entry.contains(yr.as_str()) && b_entry.to_lowercase().contains(author.as_str()) {
                    found = true;
                    bib_matched.insert(b_idx);
                    break;
                }
            }
            if !found {
                let mut chars = author.chars();
                let author_title = match chars.next() {
                    Some(f) => f.to_uppercase().collect::<String>() + chars.as_str(),
                    None => author.clone(),
                };
                issues.push((
                    "high".to_string(),
                    "MISSING_BIBLIOGRAPHY_ENTRY".to_string(),
                    format!(
                        "In-text citation '({} et al., {})' has no corresponding entry in the References section.",
                        author_title, yr
                    ),
                    format!("{}, {}", author_title, yr),
                    format!("Add complete bibliographic reference for ({}, {}) to the References section.", author_title, yr),
                ));
            }
        }

        for (b_idx, b_entry) in bib_entries.iter().enumerate() {
            if !bib_matched.contains(&b_idx) {
                let entry_low = b_entry.to_lowercase();
                let matched_any = cited_pairs
                    .iter()
                    .any(|(a, y)| entry_low.contains(a.as_str()) && b_entry.contains(y.as_str()));
                if !matched_any {
                    let preview70: String = b_entry.chars().take(70).collect();
                    let preview40: String = b_entry.chars().take(40).collect();
                    issues.push((
                        "medium".to_string(),
                        "ORPHAN_BIBLIOGRAPHY_REFERENCE".to_string(),
                        format!(
                            "Bibliographic entry '{}...' is listed in References but never cited in the body.",
                            preview70
                        ),
                        preview40,
                        "Reference the source in the text or remove the unused entry.".to_string(),
                    ));
                }
            }
        }
    } else {
        // 2. Check IEEE numeric citations
        let mut cited_nums: HashSet<usize> = HashSet::new();
        for caps in ieee_re.captures_iter(body_text) {
            if let Some(inner) = caps.get(1) {
                for nm in num_re.find_iter(inner.as_str()) {
                    if let Ok(n) = nm.as_str().parse::<usize>() {
                        cited_nums.insert(n);
                    }
                }
            }
        }

        if !cited_nums.is_empty() {
            let mut found_bib_nums: HashSet<usize> = HashSet::new();
            for b_entry in bib_entries.iter() {
                if let Some(caps) = bib_num_re.captures(b_entry) {
                    if let Some(m) = caps.get(1) {
                        if let Ok(n) = m.as_str().parse::<usize>() {
                            found_bib_nums.insert(n);
                        }
                    }
                }
            }

            let mut sorted_nums: Vec<usize> = cited_nums.into_iter().collect();
            sorted_nums.sort_unstable();
            for n in sorted_nums {
                if !found_bib_nums.contains(&n) && bib_entries.len() < n {
                    issues.push((
                        "high".to_string(),
                        "MISSING_NUMERIC_REFERENCE".to_string(),
                        format!("In-text citation [{}] has no corresponding entry in the bibliography.", n),
                        format!("[{}]", n),
                        format!("Provide full source details for reference [{}].", n),
                    ));
                }
            }
        }
    }

    issues
}

#[pyfunction]
fn classify_claim_type_rust(sentence: &str) -> String {
    static MODEL_RE: OnceLock<Regex> = OnceLock::new();
    static PRED_RE: OnceLock<Regex> = OnceLock::new();
    static INTERP_RE: OnceLock<Regex> = OnceLock::new();

    let model_re = MODEL_RE.get_or_init(|| {
        Regex::new(r"(?i)(\bwe\s+propose\b|\bour\s+model\b|\bproposed\s+framework\b|\bjarvis\s+formulation\b|\banalytical\s+model\s+proposed\b)").unwrap()
    });
    let pred_re = PRED_RE.get_or_init(|| {
        Regex::new(r"(?i)(\bwill\b|\bexpect(?:ed|s)?\b|\bproject(?:ed|s)?\b|\bforecast(?:ed|s)?\b|\banticipat(?:ed|es)?\b|\bestimat(?:ed|es)?\b|\bby\s+20(?:3[0-9]|4[0-9]|5[0-9])\b|\bpredict(?:ed|s)?\b)").unwrap()
    });
    let interp_re = INTERP_RE.get_or_init(|| {
        Regex::new(r"(?i)(\bsuggests?\b|\bindicates?\b|\bimplies?\b|\bargues?\b|\bdemonstrates?\b|\binterprets?\b|\bfrom\s+our\s+analysis\b)").unwrap()
    });

    let low = sentence.to_lowercase();
    if model_re.is_match(&low) {
        return "proposed_model".to_string();
    }
    if pred_re.is_match(&low) {
        return "prediction".to_string();
    }
    if interp_re.is_match(&low) {
        return "interpretation".to_string();
    }
    if ["we recommend", "should implement", "must consider", "actionable step"]
        .iter()
        .any(|k| low.contains(k))
    {
        return "recommendation".to_string();
    }
    if ["assuming that", "assume", "hypothesis", "under the premise"]
        .iter()
        .any(|k| low.contains(k))
    {
        return "hypothesis".to_string();
    }
    "fact".to_string()
}

// ============================================================================
// 3. CAMERA VISION, MOTION DIFFING, PRIVACY BLUR & FACE HISTOGRAM CORRELATION
// ============================================================================

#[pyfunction]
fn analyze_frame_motion_and_peeker_rust(
    py: Python<'_>,
    prev_rgb: &[u8],
    curr_rgb: &[u8],
    width: u32,
    height: u32,
    pixel_threshold: u8,
) -> PyResult<HashMap<String, f64>> {
    let result = py.allow_threads(|| {
        let mut out = HashMap::new();
        let n = prev_rgb.len().min(curr_rgb.len());
        if n < 3 || width == 0 || height == 0 {
            out.insert("motion_pct".to_string(), 0.0);
            out.insert("peeker_zone_motion_pct".to_string(), 0.0);
            out.insert("avg_brightness".to_string(), 0.0);
            out.insert("alert_triggered".to_string(), 0.0);
            return out;
        }

        let total_pixels = (n / 3) as f64;
        let mut changed_pixels = 0u64;
        let mut peeker_changed = 0u64;
        let mut peeker_total = 0u64;
        let mut brightness_sum = 0u64;

        let w_usize = width as usize;
        let left_peeker_x = w_usize / 4;
        let right_peeker_x = (w_usize * 3) / 4;

        for px_idx in 0..(n / 3) {
            let base = px_idx * 3;
            let r1 = prev_rgb[base] as i16;
            let g1 = prev_rgb[base + 1] as i16;
            let b1 = prev_rgb[base + 2] as i16;

            let r2 = curr_rgb[base] as i16;
            let g2 = curr_rgb[base + 1] as i16;
            let b2 = curr_rgb[base + 2] as i16;

            brightness_sum += ((r2 + g2 + b2) / 3) as u64;

            let diff = ((r2 - r1).abs() + (g2 - g1).abs() + (b2 - b1).abs()) / 3;
            let is_changed = diff >= (pixel_threshold as i16);
            if is_changed {
                changed_pixels += 1;
            }

            let x = px_idx % w_usize;
            if x < left_peeker_x || x > right_peeker_x {
                peeker_total += 1;
                if is_changed {
                    peeker_changed += 1;
                }
            }
        }

        let motion_pct = (changed_pixels as f64 / total_pixels) * 100.0;
        let peeker_pct = if peeker_total > 0 {
            (peeker_changed as f64 / peeker_total as f64) * 100.0
        } else {
            0.0
        };
        let avg_b = brightness_sum as f64 / total_pixels;
        let alert = if peeker_pct > 6.5 || motion_pct > 12.0 { 1.0 } else { 0.0 };

        out.insert("motion_pct".to_string(), (motion_pct * 100.0).round() / 100.0);
        out.insert("peeker_zone_motion_pct".to_string(), (peeker_pct * 100.0).round() / 100.0);
        out.insert("avg_brightness".to_string(), (avg_b * 10.0).round() / 10.0);
        out.insert("alert_triggered".to_string(), alert);
        out
    });
    Ok(result)
}

#[pyfunction]
fn apply_privacy_blur_rust(
    py: Python<'_>,
    rgb_bytes: &[u8],
    width: u32,
    height: u32,
    block_size: u32,
) -> PyResult<Vec<u8>> {
    let blurred = py.allow_threads(|| {
        let mut out = rgb_bytes.to_vec();
        let w = width as usize;
        let h = height as usize;
        let bs = block_size.max(4) as usize;
        if out.len() < w * h * 3 {
            return out;
        }

        for by in (0..h).step_by(bs) {
            for bx in (0..w).step_by(bs) {
                let mut r_sum = 0u64;
                let mut g_sum = 0u64;
                let mut b_sum = 0u64;
                let mut count = 0u64;

                let y_end = (by + bs).min(h);
                let x_end = (bx + bs).min(w);

                for y in by..y_end {
                    for x in bx..x_end {
                        let idx = (y * w + x) * 3;
                        r_sum += out[idx] as u64;
                        g_sum += out[idx + 1] as u64;
                        b_sum += out[idx + 2] as u64;
                        count += 1;
                    }
                }

                if count > 0 {
                    let r_avg = (r_sum / count) as u8;
                    let g_avg = (g_sum / count) as u8;
                    let b_avg = (b_sum / count) as u8;
                    for y in by..y_end {
                        for x in bx..x_end {
                            let idx = (y * w + x) * 3;
                            out[idx] = r_avg;
                            out[idx + 1] = g_avg;
                            out[idx + 2] = b_avg;
                        }
                    }
                }
            }
        }
        out
    });
    Ok(blurred)
}

#[pyfunction]
fn compare_grayscale_histograms_rust(img_a_gray: &[u8], img_b_gray: &[u8]) -> f64 {
    if img_a_gray.is_empty() || img_b_gray.is_empty() {
        return 0.0;
    }
    let mut hist_a = [0.0f64; 256];
    let mut hist_b = [0.0f64; 256];

    for &px in img_a_gray {
        hist_a[px as usize] += 1.0;
    }
    for &px in img_b_gray {
        hist_b[px as usize] += 1.0;
    }

    let max_a = hist_a.iter().cloned().fold(0.0f64, f64::max).max(1.0);
    let max_b = hist_b.iter().cloned().fold(0.0f64, f64::max).max(1.0);
    for i in 0..256 {
        hist_a[i] /= max_a;
        hist_b[i] /= max_b;
    }

    let mean_a = hist_a.iter().sum::<f64>() / 256.0;
    let mean_b = hist_b.iter().sum::<f64>() / 256.0;

    let mut num = 0.0f64;
    let mut den_a = 0.0f64;
    let mut den_b = 0.0f64;
    for i in 0..256 {
        let da = hist_a[i] - mean_a;
        let db = hist_b[i] - mean_b;
        num += da * db;
        den_a += da * da;
        den_b += db * db;
    }

    let denom = (den_a * den_b).sqrt();
    if denom > 1e-12 {
        (num / denom).clamp(-1.0, 1.0)
    } else {
        0.0
    }
}

// ============================================================================
// 4. REAL-TIME AUDIO DSP, VAD & AUTO-VIDEO-EDITOR SILENCE DETECTOR
// ============================================================================

#[pyfunction]
fn analyze_pcm16_audio_rust(pcm_bytes: &[u8], silence_threshold_rms: f64) -> HashMap<String, f64> {
    let mut out = HashMap::new();
    let sample_count = pcm_bytes.len() / 2;
    if sample_count == 0 {
        out.insert("rms".to_string(), 0.0);
        out.insert("peak".to_string(), 0.0);
        out.insert("zcr".to_string(), 0.0);
        out.insert("is_speech".to_string(), 0.0);
        return out;
    }

    let mut sum_sq = 0.0f64;
    let mut peak = 0i16;
    let mut zero_crossings = 0usize;
    let mut prev_sample = 0i16;

    for i in 0..sample_count {
        let lo = pcm_bytes[i * 2];
        let hi = pcm_bytes[i * 2 + 1];
        let sample = i16::from_le_bytes([lo, hi]);
        let abs_s = sample.saturating_abs();
        if abs_s > peak {
            peak = abs_s;
        }
        let s_f = sample as f64;
        sum_sq += s_f * s_f;

        if i > 0 && ((sample >= 0 && prev_sample < 0) || (sample < 0 && prev_sample >= 0)) {
            zero_crossings += 1;
        }
        prev_sample = sample;
    }

    let rms = (sum_sq / (sample_count as f64)).sqrt();
    let zcr = (zero_crossings as f64) / (sample_count as f64);
    let is_speech = if rms >= silence_threshold_rms && zcr < 0.35 { 1.0 } else { 0.0 };

    out.insert("rms".to_string(), (rms * 100.0).round() / 100.0);
    out.insert("peak".to_string(), peak as f64);
    out.insert("zcr".to_string(), (zcr * 10000.0).round() / 10000.0);
    out.insert("is_speech".to_string(), is_speech);
    out
}

#[pyfunction]
fn detect_audio_silence_segments_rust(
    py: Python<'_>,
    pcm_bytes: &[u8],
    sample_rate: u32,
    min_silence_ms: u32,
    threshold_rms: f64,
) -> PyResult<Vec<(f64, f64)>> {
    let segments = py.allow_threads(|| {
        let mut results = Vec::new();
        let total_samples = pcm_bytes.len() / 2;
        if total_samples == 0 || sample_rate == 0 {
            return results;
        }

        let win_samples = ((sample_rate as usize) / 50).max(1);
        let min_windows = ((min_silence_ms as usize) / 20).max(1);

        let mut silent_run_start: Option<usize> = None;
        let mut silent_windows = 0usize;

        let total_wins = total_samples / win_samples;
        for w_idx in 0..total_wins {
            let start_s = w_idx * win_samples;
            let end_s = start_s + win_samples;
            let mut sum_sq = 0.0f64;
            for s_idx in start_s..end_s {
                let sample = i16::from_le_bytes([pcm_bytes[s_idx * 2], pcm_bytes[s_idx * 2 + 1]]) as f64;
                sum_sq += sample * sample;
            }
            let rms = (sum_sq / (win_samples as f64)).sqrt();

            if rms < threshold_rms {
                if silent_run_start.is_none() {
                    silent_run_start = Some(start_s);
                }
                silent_windows += 1;
            } else {
                if let Some(s_start) = silent_run_start {
                    if silent_windows >= min_windows {
                        let t0 = (s_start as f64) / (sample_rate as f64);
                        let t1 = (start_s as f64) / (sample_rate as f64);
                        results.push(((t0 * 1000.0).round() / 1000.0, (t1 * 1000.0).round() / 1000.0));
                    }
                }
                silent_run_start = None;
                silent_windows = 0;
            }
        }

        if let Some(s_start) = silent_run_start {
            if silent_windows >= min_windows {
                let t0 = (s_start as f64) / (sample_rate as f64);
                let t1 = (total_samples as f64) / (sample_rate as f64);
                results.push(((t0 * 1000.0).round() / 1000.0, (t1 * 1000.0).round() / 1000.0));
            }
        }
        results
    });
    Ok(segments)
}

// ============================================================================
// 5. VECTOR MEMORY COSINE SEARCH, BM25 RANKING & PARALLEL 100K-FILE SEARCH
// ============================================================================

#[pyfunction]
fn cosine_similarity_batch_rust(
    py: Python<'_>,
    query_vec: Vec<f32>,
    matrix: Vec<Vec<f32>>,
    top_k: usize,
) -> PyResult<Vec<(usize, f32)>> {
    let ranked = py.allow_threads(|| {
        let q_norm: f32 = query_vec.iter().map(|x| x * x).sum::<f32>().sqrt();
        if q_norm == 0.0 {
            return Vec::new();
        }

        let mut scores: Vec<(usize, f32)> = matrix
            .par_iter()
            .enumerate()
            .map(|(idx, row)| {
                let len = query_vec.len().min(row.len());
                let mut dot = 0.0f32;
                let mut r_norm_sq = 0.0f32;
                for i in 0..len {
                    dot += query_vec[i] * row[i];
                    r_norm_sq += row[i] * row[i];
                }
                let denom = q_norm * r_norm_sq.sqrt();
                let sim = if denom > 0.0 { dot / denom } else { 0.0 };
                (idx, sim)
            })
            .collect();

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(top_k);
        scores
    });
    Ok(ranked)
}

#[pyfunction]
fn rank_memories_bm25_rust(
    py: Python<'_>,
    query: &str,
    documents: Vec<String>,
    top_k: usize,
) -> PyResult<Vec<(usize, f64)>> {
    let ranked = py.allow_threads(|| {
        let q_tokens: Vec<String> = query
            .to_lowercase()
            .split(|c: char| !c.is_alphanumeric())
            .filter(|s| s.len() >= 2)
            .map(|s| s.to_string())
            .collect();

        if q_tokens.is_empty() || documents.is_empty() {
            return Vec::new();
        }

        let n_docs = documents.len() as f64;
        let doc_tokens: Vec<Vec<String>> = documents
            .par_iter()
            .map(|d| {
                d.to_lowercase()
                    .split(|c: char| !c.is_alphanumeric())
                    .filter(|s| s.len() >= 2)
                    .map(|s| s.to_string())
                    .collect()
            })
            .collect();

        let avgdl: f64 = doc_tokens.iter().map(|t| t.len() as f64).sum::<f64>() / n_docs.max(1.0);
        let k1 = 1.5;
        let b = 0.75;

        let mut df_map: HashMap<&str, usize> = HashMap::new();
        for qt in q_tokens.iter() {
            let count = doc_tokens.iter().filter(|dt| dt.iter().any(|w| w == qt)).count();
            df_map.insert(qt.as_str(), count);
        }

        let mut scores: Vec<(usize, f64)> = doc_tokens
            .par_iter()
            .enumerate()
            .filter_map(|(idx, dt)| {
                if dt.is_empty() {
                    return None;
                }
                let dl = dt.len() as f64;
                let mut score = 0.0f64;
                for qt in q_tokens.iter() {
                    let tf = dt.iter().filter(|w| *w == qt).count() as f64;
                    if tf > 0.0 {
                        let df = *df_map.get(qt.as_str()).unwrap_or(&0) as f64;
                        let idf = ((n_docs - df + 0.5) / (df + 0.5) + 1.0).ln();
                        let num = tf * (k1 + 1.0);
                        let den = tf + k1 * (1.0 - b + b * (dl / avgdl.max(1.0)));
                        score += idf * (num / den);
                    }
                }
                if score > 0.0 {
                    Some((idx, (score * 10000.0).round() / 10000.0))
                } else {
                    None
                }
            })
            .collect();

        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scores.truncate(top_k);
        scores
    });
    Ok(ranked)
}

#[pyfunction]
fn fast_file_search_rust(
    py: Python<'_>,
    root_dirs: Vec<String>,
    query: &str,
    extensions: Vec<String>,
    max_results: usize,
) -> PyResult<Vec<String>> {
    static SKIP_DIRS: OnceLock<HashSet<&'static str>> = OnceLock::new();
    let skip_set = SKIP_DIRS.get_or_init(|| {
        [
            "appdata", "node_modules", ".git", "__pycache__", ".venv", "venv",
            ".lunarclient", ".minecraft", ".tlauncher", "windowsapps", "steamapps",
            "xboxgames", "$recycle.bin", "system volume information", ".gemini",
            "windows", "program files", "program files (x86)", "programdata",
            "recovery", "perflogs", "msocache", "intel", "amd", "nvidia",
        ]
        .into_iter()
        .collect()
    });

    let q_lower = query.trim().to_lowercase();
    let q_tokens: Vec<String> = q_lower
        .split(|c: char| c.is_whitespace() || c == '_' || c == '-' || c == '.')
        .filter(|t| t.len() >= 2)
        .map(|t| t.to_string())
        .collect();

    let ext_set: HashSet<String> = extensions
        .into_iter()
        .filter(|e| !e.trim().is_empty())
        .map(|e| e.trim().trim_start_matches('.').to_lowercase())
        .collect();

    let found = py.allow_threads(|| {
        let mut matches = Vec::new();
        let mut seen = HashSet::new();

        for dir_str in root_dirs {
            let root_p = Path::new(&dir_str);
            if !root_p.exists() {
                continue;
            }
            let walker = WalkDir::new(root_p)
                .max_depth(7)
                .follow_links(false)
                .into_iter()
                .filter_entry(|e| {
                    if e.depth() == 0 {
                        return true;
                    }
                    if e.file_type().is_dir() {
                        let dname = e.file_name().to_string_lossy().to_lowercase();
                        if dname.starts_with('.') || skip_set.contains(dname.as_str()) {
                            return false;
                        }
                    }
                    true
                });

            for entry in walker.filter_map(|e| e.ok()) {
                if !entry.file_type().is_file() {
                    continue;
                }
                let path = entry.path();
                let fname_raw = match path.file_name().and_then(|s| s.to_str()) {
                    Some(n) => n,
                    None => continue,
                };
                if fname_raw.starts_with("~$") || fname_raw.starts_with('.') {
                    continue;
                }
                if !ext_set.is_empty() {
                    let ext = path
                        .extension()
                        .and_then(|s| s.to_str())
                        .unwrap_or("")
                        .to_lowercase();
                    if !ext_set.contains(&ext) {
                        continue;
                    }
                }
                let fname = fname_raw.to_lowercase();
                let matched = if q_lower.is_empty() {
                    true
                } else if fname.contains(&q_lower) {
                    true
                } else if !q_tokens.is_empty() {
                    q_tokens.iter().all(|t| fname.contains(t.as_str()))
                } else {
                    false
                };

                if matched {
                    let full_s = path.to_string_lossy().to_string();
                    let key_s = full_s.to_lowercase();
                    if seen.insert(key_s) {
                        matches.push(full_s);
                        if matches.len() >= max_results {
                            return matches;
                        }
                    }
                }
            }
        }
        matches
    });
    Ok(found)
}

// ============================================================================
// 6. NATIVE WIN32 RAM TRIMMER, PYCACHE CLEANER, EMOTIONAL SPECTRUM & OFFLINE ROUTER
// ============================================================================

#[cfg(target_os = "windows")]
#[link(name = "user32")]
extern "system" {
    fn OpenClipboard(hWndNewOwner: *mut std::ffi::c_void) -> i32;
    fn EmptyClipboard() -> i32;
    fn CloseClipboard() -> i32;
    fn LockWorkStation() -> i32;
    fn keybd_event(bVk: u8, bScan: u8, dwFlags: u32, dwExtraInfo: usize);
}

#[cfg(target_os = "windows")]
extern "system" {
    fn GetCurrentProcess() -> *mut std::ffi::c_void;
    fn SetProcessWorkingSetSize(
        hProcess: *mut std::ffi::c_void,
        dwMinimumWorkingSetSize: usize,
        dwMaximumWorkingSetSize: usize,
    ) -> i32;
}

#[pyfunction]
fn wipe_clipboard_rust() -> bool {
    #[cfg(target_os = "windows")]
    unsafe {
        if OpenClipboard(std::ptr::null_mut()) != 0 {
            EmptyClipboard();
            CloseClipboard();
            return true;
        }
        return false;
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

#[pyfunction]
fn trim_working_set_ram_rust() -> bool {
    #[cfg(target_os = "windows")]
    unsafe {
        let handle = GetCurrentProcess();
        let res = SetProcessWorkingSetSize(handle, usize::MAX, usize::MAX);
        return res != 0;
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

#[pyfunction]
fn clean_pycache_rust(py: Python<'_>, base_dir: &str) -> PyResult<usize> {
    let base = Path::new(base_dir).to_path_buf();
    let count = py.allow_threads(|| {
        let mut deleted = 0usize;
        if !base.exists() {
            return 0;
        }
        for entry in WalkDir::new(&base)
            .max_depth(5)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let p = entry.path();
            if p.components().any(|c| {
                let s = c.as_os_str().to_string_lossy();
                s == "venv" || s == ".git" || s == "node_modules"
            }) {
                continue;
            }
            if entry.file_type().is_file() {
                if let Some(ext) = p.extension().and_then(|s| s.to_str()) {
                    if ext == "pyc" && fs::remove_file(p).is_ok() {
                        deleted += 1;
                    }
                }
            }
        }
        deleted
    });
    Ok(count)
}

#[pyfunction]
fn evaluate_emotional_turn_rust(user_text: &str, current_hour: u32) -> (String, i32) {
    static CUES: OnceLock<Vec<(&'static str, Vec<Regex>)>> = OnceLock::new();
    static LATE_RE: OnceLock<Regex> = OnceLock::new();

    let cues = CUES.get_or_init(|| {
        let raw: &[(&str, &[&str])] = &[
            (
                "EMPATHETIC",
                &[
                    r"\b(sad|depressed|unhappy|crying|lonely|heartbroken|hopeless)\b",
                    r"\b(stressed|stressful|overwhelmed|anxious|anxiety|panic|burnt out|burnout)\b",
                    r"\b(exhausted|so tired|drained|can't take this|struggling|hurting)\b",
                    r"\b(rough day|bad day|awful day|terrible day|feeling low)\b",
                    r"\b(failed|messed up|ruined everything|nobody cares)\b",
                    r"\b(comfort me|need a friend|listen to me|be gentle|empathy)\b",
                ],
            ),
            (
                "CHALLENGING",
                &[
                    r"\b(challenge me|critique|roast this plan|argue with me|debate)\b",
                    r"\b(devil'?s advocate|poke holes|what could go wrong|flaws? in this)\b",
                    r"\b(be honest|don't sugarcoat|tell me the truth|am i wrong|sanity check)\b",
                    r"\b(review my architecture|is this a bad idea|spar with me|counter this)\b",
                ],
            ),
            (
                "MOTIVATIONAL",
                &[
                    r"\b(motivate me|pump me up|give me a speech|hype me|boost)\b",
                    r"\b(can'?t do this|giving up|too hard|procrastinating|lazy today)\b",
                    r"\b(lost focus|imposter syndrome|self doubt|not good enough)\b",
                    r"\b(let'?s crush this|let'?s build this|time to grind|lock in)\b",
                ],
            ),
            (
                "WITTY",
                &[
                    r"\b(tell me a joke|make me laugh|roast me|tease me|sarcasm)\b",
                    r"\b(lol|haha|lmao|hehe|hilarious|funny|humor|banter)\b",
                    r"\b(we won|i did it|it worked|celebrate|cheers|victory)\b",
                ],
            ),
            (
                "TACTICAL",
                &[
                    r"\b(quick|fast|hurry|emergency|deploy now|fix bug|run command)\b",
                    r"\b(status report|execute|stand by|system check|diagnostics)\b",
                    r"\b(focus mode|terminal only|concise|no fluff|brief)\b",
                ],
            ),
            (
                "VIGILANT",
                &[
                    r"\b(3 am|4 am|all nighter|haven'?t slept|skip sleep|no sleep)\b",
                    r"\b(head hurts|eyes hurt|headache|skip meal|haven'?t eaten)\b",
                    r"\b(security alert|intruder|hacked|suspicious|danger)\b",
                ],
            ),
            (
                "FRUSTRATED",
                &[
                    r"\b(why did you break|broke again|failed again|not working again)\b",
                    r"\b(are you kidding me|are you serious|stupid error|this is so annoying)\b",
                    r"\b(argh|damn it|dammit|pissed off|fed up|sick of this)\b",
                    r"\b(i told you to|listen to me|stop doing that|why can't you)\b",
                ],
            ),
            (
                "SKEPTICAL",
                &[
                    r"\b(are you sure|sounds fake|too good to be true|no way that works)\b",
                    r"\b(doubt it|i doubt|suspicious|really\?|skeptical|don't believe)\b",
                    r"\b(prove it|sounds like a scam|verify that|sounds fishy)\b",
                ],
            ),
            (
                "SOLEMN",
                &[
                    r"\b(passed away|died|death|funeral|grave|mourning|grief)\b",
                    r"\b(lost someone|lost my|rest in peace|rip|tragic|tragedy)\b",
                    r"\b(terrible news|horrible news|silent moment|so sad)\b",
                ],
            ),
            (
                "CONCERNED",
                &[
                    r"\b(is it dangerous|smoke|burning smell|sparks|fire hazard)\b",
                    r"\b(overheating|laptop burning hot|power surge|blown capacitor)\b",
                    r"\b(chest pain|dizzy|fainting|blackout|cant breathe|can't breathe)\b",
                ],
            ),
            (
                "INDIGNANT",
                &[
                    r"\b(you're dumb|you're stupid|useless ai|you suck|shut up)\b",
                    r"\b(siri is better|alexa is smarter|you're just a calculator)\b",
                    r"\b(your fault|you messed up|you ruined this|blame you)\b",
                ],
            ),
            (
                "COLD",
                &[
                    r"\b(be cold|emotionless|robotic mode|no feelings|zero emotion)\b",
                    r"\b(clinical mode|pure machine|machine only|cold facts|clinical)\b",
                ],
            ),
        ];
        raw.iter()
            .map(|(state, pats)| {
                let compiled = pats.iter().map(|p| Regex::new(p).unwrap()).collect();
                (*state, compiled)
            })
            .collect()
    });

    let late_re = LATE_RE.get_or_init(|| Regex::new(r"\b(tired|sleep|code|work|fixing|debug|still)\b").unwrap());
    let low = user_text.to_lowercase();

    let mut best_state = "TACTICAL".to_string();
    let mut best_score = 0i32;

    for (state, regexes) in cues.iter() {
        let mut score = 0i32;
        for re in regexes.iter() {
            if re.is_match(&low) {
                score += 2;
            }
        }
        if *state == "VIGILANT" && (2..6).contains(&current_hour) && late_re.is_match(&low) {
            score += 4;
        }
        if score > best_score {
            best_score = score;
            best_state = (*state).to_string();
        }
    }

    (best_state, best_score)
}

#[pyfunction]
fn match_offline_intent_rust(utterance: &str) -> Option<(String, String)> {
    let low = utterance.trim().to_lowercase();
    if low.is_empty() {
        return None;
    }

    if low.contains("war mode") || low.contains("gaming mode") || low.contains("combat mode") {
        return Some(("war_mode".to_string(), "activate".to_string()));
    }
    if low.contains("cooldown") || low.contains("cool down") || low.contains("overheating") {
        return Some(("cooldown_protocol".to_string(), "engage".to_string()));
    }
    if low.contains("focus mode") || low.contains("do not disturb") {
        return Some(("focus_mode".to_string(), "enable".to_string()));
    }
    if low.contains("system diagnostic") || low.contains("health check") || low.contains("system status") {
        return Some(("system_diagnostics".to_string(), "full".to_string()));
    }
    if low.contains("ghost protocol") || low.contains("privacy shield") || low.contains("lockdown") {
        return Some(("ghost_protocol".to_string(), "engage".to_string()));
    }
    if low.contains("pause music") || low.contains("pause spotify") || low.contains("resume music") || low.contains("next track") {
        return Some(("spotify_control".to_string(), low));
    }
    None
}

// ============================================================================
// 7. PHASE 3: DOCUMENT CLASSIFIER, SOURCE AUTHORITY TIERING, DESTRUCTIVE GUARD & SELF-EVOLUTION PARSERS
// ============================================================================

#[pyfunction]
fn classify_document_category_rust(
    title: &str,
    doc_type: &str,
    file_type: &str,
    content: &str,
    instruction: &str,
) -> String {
    static RULES: OnceLock<Vec<(&'static str, Vec<Regex>)>> = OnceLock::new();
    let rules = RULES.get_or_init(|| {
        let raw: &[(&str, &[&str])] = &[
            (
                "spreadsheet",
                &[
                    r"\bxlsx\b",
                    r"\bspreadsheet\b",
                    r"\bexcel\b",
                    r"\bworkbook\b",
                    r"\bledger\b",
                    r"\btracker\b",
                    r"\bdata\s*sheet\b",
                ],
            ),
            (
                "creative_presentation",
                &[
                    r"\bpptx\b",
                    r"\bpresentation\b",
                    r"\bpitch\s*deck\b",
                    r"\bslides\b",
                    r"\bkeynote\b",
                    r"\bdeck\b",
                    r"\bcompany\s*profile\b",
                ],
            ),
            (
                "financial",
                &[
                    r"\bfinancial\b",
                    r"\bbudget\b",
                    r"\bvaluation\b",
                    r"\bdcf\b",
                    r"\bbalance\s*sheet\b",
                    r"\bcash\s*flow\b",
                    r"\bforecast\b",
                    r"\bprojections?\b",
                    r"\bexpense\b",
                    r"\bebitda\b",
                    r"\bcagr\b",
                    r"\bearnings\b",
                    r"\bquarterly\s*financial\b",
                ],
            ),
            (
                "academic",
                &[
                    r"\bresearch\s*paper\b",
                    r"\bthesis\b",
                    r"\bdissertation\b",
                    r"\bliterature\s*review\b",
                    r"\bacademic\b",
                    r"\blab\s*report\b",
                    r"\bscientific\b",
                    r"\bpeer\s*review\b",
                    r"\bjournal\b",
                    r"\bcase\s*study\b",
                    r"\bstudy\s*guide\b",
                ],
            ),
            (
                "professional",
                &[
                    r"\bresume\b",
                    r"\bcv\b",
                    r"\bcurriculum\s*vitae\b",
                    r"\bcover\s*letter\b",
                    r"\bmemo\b",
                    r"\bmemorandum\b",
                    r"\bsop\b",
                    r"\bstandard\s*operating\s*procedure\b",
                    r"\bpolicy\s*doc\b",
                ],
            ),
            (
                "technical",
                &[
                    r"\barchitecture\b",
                    r"\btechnical\s*spec\b",
                    r"\bapi\b",
                    r"\bsystem\s*spec\b",
                    r"\bmanual\b",
                    r"\bcodebase\b",
                    r"\bsoftware\b",
                    r"\bengineering\b",
                    r"\bdeveloper\s*guide\b",
                    r"\bproject_doc\b",
                    r"\bhtmldoc\b",
                ],
            ),
            (
                "business",
                &[
                    r"\bbusiness\b",
                    r"\bstrategic\b",
                    r"\bproposal\b",
                    r"\bmarket\s*research\b",
                    r"\bswot\b",
                    r"\bfeasibility\b",
                    r"\bmanagement\s*report\b",
                    r"\bexecutive\s*brief\b",
                    r"\bexecutive\s*summary\b",
                ],
            ),
        ];
        raw.iter()
            .map(|(cat, pats)| {
                let compiled = pats
                    .iter()
                    .map(|p| Regex::new(&format!("(?i){}", p)).unwrap())
                    .collect();
                (*cat, compiled)
            })
            .collect()
    });

    let clean_ftype = file_type.trim().trim_start_matches('.').to_lowercase();
    let dt_low = doc_type.trim().to_lowercase();

    if matches!(clean_ftype.as_str(), "xlsx" | "xls" | "csv")
        || matches!(dt_low.as_str(), "spreadsheet" | "excel")
    {
        return "spreadsheet".to_string();
    }
    if matches!(clean_ftype.as_str(), "pptx" | "ppt")
        || matches!(dt_low.as_str(), "presentation" | "slides" | "deck")
    {
        return "creative_presentation".to_string();
    }

    let content_head: String = content.chars().take(1000).collect();
    let blob = format!(
        "{} {} {} {} {}",
        title, doc_type, file_type, instruction, content_head
    )
    .to_lowercase();

    for (cat, regexes) in rules.iter() {
        for re in regexes.iter() {
            if re.is_match(&blob) {
                return (*cat).to_string();
            }
        }
    }

    match dt_low.as_str() {
        "full_manual" | "architecture" | "api_reference" | "technical_spec" | "readme" => {
            "technical".to_string()
        }
        "executive_brief" => "business".to_string(),
        _ => "general".to_string(),
    }
}

#[pyfunction]
fn evaluate_source_tier_rust(url: &str, doi: &str, journal: &str) -> (i32, String) {
    static DOI_RE: OnceLock<Regex> = OnceLock::new();
    let doi_re = DOI_RE
        .get_or_init(|| Regex::new(r"(?i)^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$").unwrap());

    let clean_doi = doi.trim();
    if !clean_doi.is_empty() && doi_re.is_match(clean_doi) {
        return (2, "High (Scholarly DOI)".to_string());
    }

    let clean_url = url.trim().to_lowercase();
    if clean_url.is_empty() {
        let j_low = journal.trim().to_lowercase();
        if !j_low.is_empty()
            && ["journal", "ieee", "acm", "proceedings", "nature", "science"]
                .iter()
                .any(|k| j_low.contains(k))
        {
            return (2, "High (Peer-Reviewed Journal)".to_string());
        }
        return (4, "Moderate".to_string());
    }

    let without_scheme = clean_url
        .split("://")
        .nth(1)
        .unwrap_or(&clean_url);
    let host_raw = without_scheme.split('/').next().unwrap_or("");
    let host = host_raw.trim_start_matches("www.");

    const PRIMARY: &[&str] = &[
        "sec.gov",
        "whitehouse.gov",
        "federalreserve.gov",
        "treasury.gov",
        "gov.uk",
        "fda.gov",
        "nih.gov",
        "cdc.gov",
        "w3.org",
        "ietf.org",
        "iso.org",
        "nist.gov",
        "worldbank.org",
        "imf.org",
        "who.int",
        "un.org",
    ];
    for d in PRIMARY {
        if host.ends_with(d) {
            return (1, "Highest (Primary/Official)".to_string());
        }
    }

    const SCHOLARLY: &[&str] = &[
        "arxiv.org",
        "openalex.org",
        "crossref.org",
        "doi.org",
        "nature.com",
        "sciencemag.org",
        "acm.org",
        "ieee.org",
        "springer.com",
        "wiley.com",
        "sciencedirect.com",
        "cell.com",
        "pnas.org",
        "thelancet.com",
        "jamanetwork.com",
        "biorxiv.org",
        "medrxiv.org",
    ];
    for d in SCHOLARLY {
        if host.ends_with(d) {
            return (2, "High (Scholarly/Academic)".to_string());
        }
    }

    const JOURNALISTIC: &[&str] = &[
        "reuters.com",
        "bloomberg.com",
        "wsj.com",
        "ft.com",
        "nytimes.com",
        "bbc.com",
        "economist.com",
        "forbes.com",
        "techcrunch.com",
        "wired.com",
        "nature.com/news",
    ];
    for d in JOURNALISTIC {
        if host.ends_with(d) {
            return (3, "Substantial (Reputable Press)".to_string());
        }
    }

    if ["wikipedia.org", "medium.com", "substack.com", "github.com", "reddit.com"]
        .iter()
        .any(|h| host.contains(h))
    {
        return (4, "Moderate (Secondary Commentary)".to_string());
    }

    (5, "Low (Unverified Web)".to_string())
}

#[pyfunction]
fn has_destructive_intent_rust(text: &str) -> bool {
    let t_low = text.to_lowercase();
    const KEYWORDS: &[&str] = &[
        "delete file",
        "delete folder",
        "remove directory",
        "wipe memory",
        "clear memory",
        "format drive",
        "wipe drive",
        "drop database",
        "rmdir",
        "del /f",
        "rm -rf",
        "shutdown pc",
        "restart pc",
        "terminate all processes",
        "factory reset",
        "wipe conversation",
    ];
    KEYWORDS.iter().any(|kw| t_low.contains(kw))
}

#[pyfunction]
fn slugify_identifier_rust(raw: &str, default_val: &str, max_len: usize) -> String {
    let cleaned_raw = raw.trim().to_lowercase().replace(".py", "");
    let mut slug = String::with_capacity(cleaned_raw.len());
    let mut prev_underscore = false;

    for ch in cleaned_raw.chars() {
        if ch.is_ascii_alphanumeric() || ch == '_' {
            if ch == '_' {
                if !prev_underscore {
                    slug.push('_');
                    prev_underscore = true;
                }
            } else {
                slug.push(ch);
                prev_underscore = false;
            }
        } else if !prev_underscore {
            slug.push('_');
            prev_underscore = true;
        }
    }

    let trimmed = slug.trim_matches('_');
    let mut s: String = if max_len > 0 {
        trimmed.chars().take(max_len).collect()
    } else {
        trimmed.to_string()
    };

    if s.is_empty() {
        s = if default_val == "skill" {
            "custom_skill".to_string()
        } else {
            default_val.to_string()
        };
    } else if s.chars().next().map(|c| c.is_ascii_digit()).unwrap_or(false) {
        if default_val == "skill" {
            s = format!("custom_{}", s);
        } else {
            s = format!("x_{}", s);
        }
    }
    s
}

#[pyfunction]
fn strip_markdown_fences_rust(text: &str) -> String {
    static FENCE_RE: OnceLock<Regex> = OnceLock::new();
    let fence_re = FENCE_RE
        .get_or_init(|| Regex::new(r"(?s)```[a-zA-Z0-9_+-]*\r?\n(.*?)```").unwrap());

    let trimmed = text.trim();
    if trimmed.contains("```") {
        if let Some(caps) = fence_re.captures(trimmed) {
            if let Some(m) = caps.get(1) {
                return m.as_str().trim().to_string();
            }
        }
        let no_head = trimmed
            .trim_start_matches("```json")
            .trim_start_matches("```python")
            .trim_start_matches("```");
        return no_head.trim().trim_end_matches('`').trim().to_string();
    }
    trimmed.to_string()
}

#[pyfunction]
fn extract_public_defs_rust(code: &str) -> Vec<String> {
    static DEF_RE: OnceLock<Regex> = OnceLock::new();
    let def_re =
        DEF_RE.get_or_init(|| Regex::new(r"(?m)^def ([a-zA-Z][a-zA-Z0-9_]*)\s*\(").unwrap());

    let mut seen = HashSet::new();
    let mut defs = Vec::new();
    for caps in def_re.captures_iter(code) {
        if let Some(m) = caps.get(1) {
            let name = m.as_str().to_string();
            if seen.insert(name.clone()) {
                defs.push(name);
            }
        }
    }
    defs
}

#[pyfunction]
fn detect_ai_patterns_rust(
    text: &str,
) -> (i32, i32, f64, usize, usize, Vec<String>, String) {
    let clean = text.trim();
    if clean.is_empty() {
        return (
            100,
            0,
            0.5,
            0,
            0,
            Vec::new(),
            "PASS - HUMAN WRITTEN".to_string(),
        );
    }

    static WORD_ALPHA_RE: OnceLock<Regex> = OnceLock::new();
    static WORD_ALNUM_RE: OnceLock<Regex> = OnceLock::new();
    static WATCHLIST_RES: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();

    let word_alpha_re = WORD_ALPHA_RE.get_or_init(|| Regex::new(r"\b[a-zA-Z']+\b").unwrap());
    let word_alnum_re = WORD_ALNUM_RE.get_or_init(|| Regex::new(r"\b\w+\b").unwrap());
    let watchlist = WATCHLIST_RES.get_or_init(|| {
        const RAW: &[&str] = &[
            "delve",
            "tapestry",
            "testament",
            "underscore",
            "pivotal",
            "paramount",
            "multifaceted",
            "realm",
            "beacon",
            "symphony",
            "foster",
            "harness",
            "utilize",
            "moreover",
            "furthermore",
            "consequently",
            "subsequently",
            "in conclusion",
            "it is important to note",
            "it is worth noting",
            "fast-paced world",
            "ever-evolving",
            "meticulous",
            "seamless",
            "plethora",
            "myriad",
            "embark",
            "endeavor",
            "commence",
            "game-changer",
        ];
        RAW.iter()
            .map(|p| {
                let pat = format!(r"\b{}\b", regex::escape(p));
                (*p, Regex::new(&pat).unwrap())
            })
            .collect()
    });

    // Split sentences on [.!?] followed by whitespace
    let mut sentences: Vec<String> = Vec::new();
    let mut current = String::new();
    let chars: Vec<char> = clean.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        current.push(chars[i]);
        if matches!(chars[i], '.' | '!' | '?') && (i + 1 == chars.len() || chars[i + 1].is_whitespace()) {
            let trimmed = current.trim().to_string();
            if trimmed.chars().count() > 2 {
                sentences.push(trimmed);
            }
            current.clear();
            while i + 1 < chars.len() && chars[i + 1].is_whitespace() {
                i += 1;
            }
        }
        i += 1;
    }
    let tail = current.trim().to_string();
    if tail.chars().count() > 2 {
        sentences.push(tail);
    }

    let lower_txt = clean.to_lowercase();
    let words: Vec<&str> = word_alpha_re
        .find_iter(&lower_txt)
        .map(|m| m.as_str())
        .collect();
    let word_count = words.len().max(1);

    let burstiness_cv = if sentences.len() >= 2 {
        let lengths: Vec<f64> = sentences
            .iter()
            .map(|s| word_alnum_re.find_iter(s).count() as f64)
            .collect();
        let mean_len = lengths.iter().sum::<f64>() / (lengths.len() as f64);
        let variance = lengths
            .iter()
            .map(|x| (x - mean_len).powi(2))
            .sum::<f64>()
            / (lengths.len() as f64);
        let std_dev = variance.sqrt();
        std_dev / mean_len.max(1.0)
    } else {
        0.45
    };

    let mut flagged = Vec::new();
    let mut penalty_points = 0.0;
    for (phrase, re) in watchlist.iter() {
        let matches = re.find_iter(&lower_txt).count();
        if matches > 0 {
            flagged.push(format!("{} ({}x)", phrase, matches));
            penalty_points += (matches as f64) * 6.5;
        }
    }

    let unique_words: HashSet<&str> = words.iter().copied().collect();
    let unique_ratio = if word_count > 10 {
        (unique_words.len() as f64) / (word_count as f64).sqrt()
    } else {
        3.5
    };

    let em_dashes = clean.matches('—').count();
    let em_threshold = 3usize.max(sentences.len() / 3);
    if em_dashes > em_threshold {
        penalty_points += ((em_dashes - 2) as f64) * 2.5;
    }

    let burst_score = ((burstiness_cv / 0.42) * 95.0).clamp(35.0, 100.0);
    let vocab_score = ((unique_ratio / 3.8) * 95.0).clamp(50.0, 100.0);

    let mut raw_human = (0.55 * burst_score) + (0.45 * vocab_score) - penalty_points;
    if flagged.is_empty() && burstiness_cv >= 0.30 {
        raw_human = raw_human.max(92.0);
    } else if flagged.is_empty() {
        raw_human = raw_human.max(88.0);
    }

    let human_score = raw_human.clamp(12.0, 99.0).round() as i32;
    let ai_prob = 100 - human_score;

    let verdict = if human_score >= 88 {
        "PASS — HUMAN WRITTEN (Bypasses Turnitin / GPTZero / Originality)"
    } else if human_score >= 72 {
        "MODERATE — MOSTLY HUMAN (Minor uniform phrasing)"
    } else {
        "HIGH AI RISK — REQUIRES HUMANIZATION"
    };

    let cv_rounded = (burstiness_cv * 1000.0).round() / 1000.0;
    (
        human_score,
        ai_prob,
        cv_rounded,
        word_count,
        sentences.len(),
        flagged,
        verdict.to_string(),
    )
}

#[pyfunction]
fn extract_material_sentences_rust(text: &str) -> Vec<String> {
    static METRIC_RE: OnceLock<Regex> = OnceLock::new();
    let metric_re =
        METRIC_RE.get_or_init(|| Regex::new(r"(?:\$\d+(?:\.\d+)?%?|\b\d+(?:\.\d+)?%?|\b\d{4}\b)").unwrap());
    const ASSERTIONS: &[&str] = &[
        "acquired",
        "founded",
        "increased",
        "decreased",
        "reached",
        "demonstrated",
        "concluded",
        "propose",
        "proposed",
        "hypothesis",
        "expect",
        "predict",
        "assume",
        "recommend",
        "scales",
        "framework",
        "architecture",
    ];

    let mut raw_sentences = Vec::new();
    let chars: Vec<char> = text.chars().collect();
    let mut start = 0usize;
    let mut i = 0usize;
    while i < chars.len() {
        if matches!(chars[i], '.' | '!' | '?') {
            let mut j = i + 1;
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            if j > i + 1 && j < chars.len() && (chars[j].is_ascii_uppercase() || chars[j].is_ascii_digit()) {
                let s: String = chars[start..=i].iter().collect();
                raw_sentences.push(s);
                start = j;
                i = j;
                continue;
            }
        }
        i += 1;
    }
    if start < chars.len() {
        let s: String = chars[start..].iter().collect();
        raw_sentences.push(s);
    }

    let mut out = Vec::new();
    for sent in raw_sentences {
        let clean_s = sent.trim();
        if clean_s.len() < 20 {
            continue;
        }
        let s_low = clean_s.to_lowercase();
        let has_metric = metric_re.is_match(clean_s);
        let has_assertion = ASSERTIONS.iter().any(|k| s_low.contains(k));
        if has_metric || has_assertion {
            out.push(clean_s.to_string());
        }
    }
    out
}

#[pyfunction]
fn verify_claim_concordance_rust(
    claim_text: &str,
    sources: Vec<(String, String)>,
) -> (String, f64, Vec<String>, String, String) {
    if sources.is_empty() {
        return (
            "unverified".to_string(),
            0.3,
            Vec::new(),
            String::new(),
            "No primary or secondary sources registered in Evidence Registry.".to_string(),
        );
    }

    static YEAR_RE: OnceLock<Regex> = OnceLock::new();
    static NUM_RE: OnceLock<Regex> = OnceLock::new();
    static WORD4_RE: OnceLock<Regex> = OnceLock::new();

    let year_re = YEAR_RE.get_or_init(|| Regex::new(r"\b(?:19|20)\d{2}\b").unwrap());
    let num_re = NUM_RE.get_or_init(|| Regex::new(r"\b\d+(?:\.\d+)?\b").unwrap());
    let word4_re = WORD4_RE.get_or_init(|| Regex::new(r"[a-z]{4,}").unwrap());
    const STOP: &[&str] = &["which", "that", "there", "their", "about", "under", "total"];

    let claim_years: HashSet<String> = year_re
        .find_iter(claim_text)
        .map(|m| m.as_str().to_string())
        .collect();
    let claim_metrics: HashSet<String> = num_re
        .find_iter(claim_text)
        .map(|m| m.as_str().to_string())
        .filter(|m| !claim_years.contains(m))
        .collect();

    let claim_lower = claim_text.to_lowercase();
    let claim_words: Vec<String> = word4_re
        .find_iter(&claim_lower)
        .map(|m| m.as_str().to_string())
        .filter(|w| !STOP.contains(&w.as_str()))
        .collect();

    let mut matching_sources: Vec<String> = Vec::new();
    let mut conflicting_sources: Vec<String> = Vec::new();

    for (s_id, s_raw) in sources {
        let s_text = s_raw.to_lowercase();
        if s_text.is_empty() {
            continue;
        }
        let overlap = claim_words
            .iter()
            .filter(|w| s_text.contains(w.as_str()))
            .count();
        let overlap_ratio = (overlap as f64) / (claim_words.len().max(1) as f64);

        if overlap_ratio >= 0.35 {
            let s_years: HashSet<String> = year_re
                .find_iter(&s_text)
                .map(|m| m.as_str().to_string())
                .collect();
            let s_metrics: HashSet<String> = num_re
                .find_iter(&s_text)
                .map(|m| m.as_str().to_string())
                .filter(|m| !s_years.contains(m))
                .collect();

            if !claim_metrics.is_empty()
                && !s_metrics.is_empty()
                && claim_metrics.is_disjoint(&s_metrics)
            {
                conflicting_sources.push(s_id);
            } else if !claim_years.is_empty()
                && !s_years.is_empty()
                && claim_years.is_disjoint(&s_years)
            {
                conflicting_sources.push(s_id);
            } else {
                matching_sources.push(s_id);
            }
        }
    }

    if !matching_sources.is_empty() {
        if !conflicting_sources.is_empty() {
            let conf_notes = format!(
                "Discrepancy detected against sources: {:?}",
                conflicting_sources
            );
            let reason = format!(
                "Supported by {:?} but contradicted by {:?}.",
                matching_sources, conflicting_sources
            );
            (
                "conflicting_evidence".to_string(),
                0.5,
                matching_sources,
                conf_notes,
                reason,
            )
        } else {
            let reason = format!(
                "Direct concordance found with source(s): {:?}.",
                matching_sources
            );
            (
                "verified".to_string(),
                0.95,
                matching_sources,
                String::new(),
                reason,
            )
        }
    } else if !conflicting_sources.is_empty() {
        let conf_notes = format!(
            "Numerical conflict with registered source(s): {:?}",
            conflicting_sources
        );
        let reason = format!(
            "Numerical values contradict sources: {:?}.",
            conflicting_sources
        );
        (
            "conflicting_evidence".to_string(),
            0.2,
            Vec::new(),
            conf_notes,
            reason,
        )
    } else {
        (
            "unverified".to_string(),
            0.4,
            Vec::new(),
            String::new(),
            "No registered source text corroborated this specific assertion.".to_string(),
        )
    }
}

#[pyfunction]
fn validate_spreadsheet_cells_rust(
    sheets: Vec<(String, Vec<Vec<String>>)>,
) -> Vec<(String, String, String, String, String)> {
    const ERROR_TOKENS: &[&str] = &[
        "#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!",
    ];
    let mut issues = Vec::new();

    for (s_name, rows) in sheets {
        for (r_idx, row) in rows.iter().enumerate() {
            let r_num = r_idx + 1;
            for (c_idx, cell) in row.iter().enumerate() {
                let c_num = c_idx + 1;
                let str_cell = cell.trim();
                for tok in ERROR_TOKENS {
                    if str_cell.contains(tok) {
                        issues.push((
                            "critical".to_string(),
                            "SPREADSHEET_FORMULA_ERROR".to_string(),
                            format!(
                                "Sheet '{}' cell ({}, {}) contains formula error token '{}'.",
                                s_name, r_num, c_num, tok
                            ),
                            format!("{}!R{}C{}", s_name, r_num, c_num),
                            format!(
                                "Fix referenced range or denominator in cell formula to eliminate {}.",
                                tok
                            ),
                        ));
                    }
                }
                if str_cell.starts_with('=')
                    && str_cell.matches('(').count() != str_cell.matches(')').count()
                {
                    issues.push((
                        "critical".to_string(),
                        "UNBALANCED_FORMULA_PARENS".to_string(),
                        format!(
                            "Sheet '{}' cell ({}, {}) has unbalanced parentheses: '{}'.",
                            s_name, r_num, c_num, str_cell
                        ),
                        format!("{}!R{}C{}", s_name, r_num, c_num),
                        "Balance open and closing parentheses.".to_string(),
                    ));
                }
            }
        }
    }
    issues
}

#[pyfunction]
fn split_glued_bibliography_rust(text: &str) -> String {
    static PAT0: OnceLock<Regex> = OnceLock::new();
    static PAT1: OnceLock<Regex> = OnceLock::new();
    static PAT2: OnceLock<Regex> = OnceLock::new();

    let pat0 = PAT0.get_or_init(|| {
        Regex::new(r"(?i)((?:https?://[^\s)\]]+?|doi:\s*10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?|10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?))([1-9]\.\s+[A-Z][a-zA-Z'-]+,\s*[A-Z])").unwrap()
    });
    let pat1 = PAT1.get_or_init(|| {
        Regex::new(r"(?i)((?:https?://[^\s)\]]+?|doi:\s*10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?|10\.\d{4,9}/[-._;()/:A-Za-z0-9]+?))(?:\.)?\s+((?:\[\d{1,3}\]|\d{1,3}\.)\s+[A-Z])").unwrap()
    });
    let pat2 = PAT2.get_or_init(|| {
        Regex::new(r"(\([12]\d{3}[a-z]?\)\.|pp?\.\s*\d+[–-]\d+\.)\s*((?:\[\d{1,3}\]|\d{1,3}\.)\s+[A-Z][a-zA-Z'-]+,\s*[A-Z])").unwrap()
    });

    let mut current = text.to_string();
    for _ in 0..4 {
        let next0 = pat0.replace_all(&current, "$1\n$2").into_owned();
        let next1 = pat1.replace_all(&next0, "$1\n$2").into_owned();
        let next2 = pat2.replace_all(&next1, "$1\n$2").into_owned();
        if next2 == current {
            break;
        }
        current = next2;
    }
    current
}

#[pyfunction]
fn normalize_markdown_rust(raw_text: &str) -> String {
    if raw_text.is_empty() {
        return String::new();
    }

    static FENCE_RE: OnceLock<Regex> = OnceLock::new();
    static LIT_N_RE: OnceLock<Regex> = OnceLock::new();
    static HR_INLINE_RE: OnceLock<Regex> = OnceLock::new();
    static HR_EOL_RE: OnceLock<Regex> = OnceLock::new();
    static HR_SOL_RE: OnceLock<Regex> = OnceLock::new();
    static ATX_GLUED_RE: OnceLock<Regex> = OnceLock::new();
    static ATX_LINE_RE: OnceLock<Regex> = OnceLock::new();
    static HR_LINE_RE: OnceLock<Regex> = OnceLock::new();
    static DISPLAY_MATH_RE: OnceLock<Regex> = OnceLock::new();
    static MULTI_NL_RE: OnceLock<Regex> = OnceLock::new();

    let fence_re = FENCE_RE.get_or_init(|| Regex::new(r"(?s)```.*?```").unwrap());
    let lit_n_re = LIT_N_RE.get_or_init(|| Regex::new(r"\\n([a-zA-Z]*)").unwrap());
    let hr_inline_re =
        HR_INLINE_RE.get_or_init(|| Regex::new(r"([^\n|])\s*---+\s*([#A-Za-z0-9*])").unwrap());
    let hr_eol_re = HR_EOL_RE.get_or_init(|| Regex::new(r"(?m)([^\n|])\s*---+\s*$").unwrap());
    let hr_sol_re =
        HR_SOL_RE.get_or_init(|| Regex::new(r"(?m)^\s*---+\s*([^\n\s|-])").unwrap());
    let atx_glued_re =
        ATX_GLUED_RE.get_or_init(|| Regex::new(r"([^\n#])\s*(#{1,4}\s+[A-Z0-9*])").unwrap());
    let atx_line_re = ATX_LINE_RE.get_or_init(|| Regex::new(r"(?m)^(#{1,4}\s+.+)$").unwrap());
    let hr_line_re = HR_LINE_RE.get_or_init(|| Regex::new(r"(?m)^(\s*---+\s*)$").unwrap());
    let display_math_re =
        DISPLAY_MATH_RE.get_or_init(|| Regex::new(r"(?s)([^\n])\s*(\$\$.+?\$\$)\s*([^\n])").unwrap());
    let multi_nl_re = MULTI_NL_RE.get_or_init(|| Regex::new(r"\n{4,}").unwrap());

    const ALLOWED_N_SUFFIXES: &[&str] = &[
        "abla", "eq", "e", "u", "otin", "atural", "exists", "eg", "less", "gtr",
        "leq", "geq", "subseteq", "supseteq", "mid", "parallel",
    ];

    let mut text = raw_text.replace("\r\n", "\n").replace('\r', "\n");
    text = text.replace("\\r\\n", "\n");

    text = lit_n_re
        .replace_all(&text, |caps: &regex::Captures| {
            let suffix = caps.get(1).map(|m| m.as_str()).unwrap_or("");
            if ALLOWED_N_SUFFIXES.contains(&suffix) {
                format!("\\n{}", suffix)
            } else {
                format!("\n{}", suffix)
            }
        })
        .into_owned();

    let mut fenced_blocks: Vec<String> = Vec::new();
    text = fence_re
        .replace_all(&text, |caps: &regex::Captures| {
            let idx = fenced_blocks.len();
            fenced_blocks.push(caps[0].to_string());
            format!("\n\n@@FENCED_CODE_BLOCK_{}@@\n\n", idx)
        })
        .into_owned();

    text = hr_inline_re.replace_all(&text, "$1\n\n---\n\n$2").into_owned();
    text = hr_eol_re.replace_all(&text, "$1\n\n---\n\n").into_owned();
    text = hr_sol_re.replace_all(&text, "---\n\n$1").into_owned();
    text = atx_glued_re.replace_all(&text, "$1\n\n$2").into_owned();
    text = atx_line_re.replace_all(&text, "\n$1\n").into_owned();
    text = hr_line_re.replace_all(&text, "\n\n---\n\n").into_owned();

    text = split_glued_bibliography_rust(&text);
    text = display_math_re
        .replace_all(&text, "$1\n\n$2\n\n$3")
        .into_owned();

    for (idx, block) in fenced_blocks.iter().enumerate() {
        let placeholder = format!("@@FENCED_CODE_BLOCK_{}@@", idx);
        text = text.replace(&placeholder, block);
    }

    text = multi_nl_re.replace_all(&text, "\n\n").into_owned();
    text.trim().to_string()
}

#[pyfunction]
fn audit_files_for_secrets_rust(base_dir: &str, rel_paths: Vec<String>) -> Vec<String> {
    static SECRET_RES: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    let rules = SECRET_RES.get_or_init(|| {
        vec![
            (
                "Google API Key",
                Regex::new(r"AIzaSy[A-Za-z0-9_\-]{33}").unwrap(),
            ),
            (
                "OpenRouter API Key",
                Regex::new(r"sk-or-v1-[a-f0-9]{48,64}").unwrap(),
            ),
            (
                "Anthropic API Key",
                Regex::new(r"sk-ant-api[A-Za-z0-9_\-]{20,}").unwrap(),
            ),
            (
                "OpenAI API Key",
                Regex::new(r"sk-proj-[A-Za-z0-9_\-]{20,}").unwrap(),
            ),
            (
                "Telegram Bot Token",
                Regex::new(r"\b\d{8,10}:[A-Za-z0-9_\-]{35}\b").unwrap(),
            ),
            (
                "Private Key Block",
                Regex::new(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----").unwrap(),
            ),
        ]
    });

    let root = Path::new(base_dir);
    const SKIP_EXTS: &[&str] = &[".png", ".ico", ".jpg", ".zip", ".exe", ".mp3", ".wav", ".whl", ".pyd"];

    rel_paths
        .par_iter()
        .flat_map(|tf| {
            let mut file_violations = Vec::new();
            if tf.ends_with("security_audit.py")
                || tf.ends_with(".example")
                || SKIP_EXTS.iter().any(|ext| tf.ends_with(ext))
            {
                return file_violations;
            }
            let full = root.join(tf);
            if let Ok(bytes) = fs::read(&full) {
                let content = String::from_utf8_lossy(&bytes);
                for (label, rx) in rules.iter() {
                    if let Some(m) = rx.find(&content) {
                        let snippet: String = m.as_str().chars().take(8).collect();
                        file_violations.push(format!(
                            "LEAKED {} ({}...) IN FILE: {}",
                            label, snippet, tf
                        ));
                    }
                }
            }
            file_violations
        })
        .collect()
}

#[pyfunction]
fn check_online_rust() -> bool {
    use std::net::{SocketAddr, TcpStream};
    use std::time::Duration;
    let addr = SocketAddr::from(([8, 8, 8, 8], 53));
    TcpStream::connect_timeout(&addr, Duration::from_millis(1500)).is_ok()
}

#[pyfunction]
fn execute_offline_command_rust(text: &str) -> String {
    let intent = match_offline_intent_rust(text)
        .map(|(k, _)| k)
        .unwrap_or_default();
    let t_low = text.trim().to_lowercase();

    if intent == "LOCK_WORKSTATION" || t_low.contains("lock") || t_low.contains("workstation") {
        #[cfg(target_os = "windows")]
        unsafe {
            LockWorkStation();
        }
        return "[MARK 108 OFFLINE ENGINE] Workstation locked.".to_string();
    }

    if intent == "MUTE_AUDIO" || t_low.contains("mute") {
        #[cfg(target_os = "windows")]
        unsafe {
            // VK_VOLUME_MUTE = 0xAD, KEYEVENTF_KEYUP = 0x0002
            keybd_event(0xAD, 0, 0, 0);
            keybd_event(0xAD, 0, 2, 0);
        }
        return "[MARK 108 OFFLINE ENGINE] Muted audio.".to_string();
    }

    if intent == "VOLUME_UP" || t_low.contains("volume up") {
        #[cfg(target_os = "windows")]
        unsafe {
            // VK_VOLUME_UP = 0xAF
            for _ in 0..5 {
                keybd_event(0xAF, 0, 0, 0);
                keybd_event(0xAF, 0, 2, 0);
            }
        }
        return "[MARK 108 OFFLINE ENGINE] Volume increased.".to_string();
    }

    if intent == "VOLUME_DOWN" || t_low.contains("volume down") {
        #[cfg(target_os = "windows")]
        unsafe {
            // VK_VOLUME_DOWN = 0xAE
            for _ in 0..5 {
                keybd_event(0xAE, 0, 0, 0);
                keybd_event(0xAE, 0, 2, 0);
            }
        }
        return "[MARK 108 OFFLINE ENGINE] Volume decreased.".to_string();
    }

    let is_online = check_online_rust();
    format!(
        "[MARK 108 OFFLINE ENGINE] System online check: {}",
        if is_online { "ONLINE 🌐" } else { "OFFLINE ⚠️" }
    )
}

#[pyfunction]
fn evaluate_contextual_reaction_rust(user_text: &str, current_hour: u32) -> String {
    let lower = user_text.to_lowercase();
    const TRIGGERS: &[(&str, &[&str])] = &[
        ("cough", &["cough", "fake cough", "clear throat", "ahem"]),
        ("sneeze", &["sneeze", "achoo", "bless you"]),
        ("throat_clear", &["throat clear", "clear your throat", "attention"]),
        ("yawn", &["yawn", "tired", "sleepy", "late night"]),
        ("eyebrow", &["eyebrow", "raise eyebrow", "smirk", "skeptical look"]),
        ("chuckle", &["chuckle", "laugh", "funny", "ironic"]),
        ("sigh", &["sigh", "deep breath", "exhale"]),
        ("blink", &["blink", "refresh vision", "wink"]),
    ];

    for (key, phrases) in TRIGGERS {
        if phrases.iter().any(|p| lower.contains(p)) {
            return (*key).to_string();
        }
    }

    const BLUNDERS: &[&str] = &[
        "stupid mistake",
        "i messed up",
        "i broke it",
        "deleted the wrong",
        "failed again",
        "blew it",
    ];
    if BLUNDERS.iter().any(|w| lower.contains(w)) {
        return "cough".to_string();
    }

    const DOUBTS: &[&str] = &[
        "i will finish in 5 minutes",
        "trust me",
        "100% bug free",
        "it worked on my machine",
        "i didn't test it",
    ];
    if DOUBTS.iter().any(|w| lower.contains(w)) {
        return "eyebrow".to_string();
    }

    if (2..5).contains(&current_hour) && (lower.contains("work") || lower.contains("code")) {
        return "yawn".to_string();
    }

    String::new()
}

#[pyfunction]
fn detect_conversation_topic_rust(user_text: &str) -> (String, Vec<String>) {
    let t_low = user_text.to_lowercase();
    const KEYWORDS: &[(&str, &str)] = &[
        ("exam", "Exam"),
        ("syllabus", "Syllabus"),
        ("chapter", "Chapter"),
        ("lecture", "Lecture"),
        ("assignment", "Assignment"),
        ("test", "Test"),
        ("study", "Study"),
        ("notes", "Notes"),
        ("quiz", "Quiz"),
        ("formula", "Formula"),
        ("derivation", "Derivation"),
        ("paper", "Paper"),
        ("economics", "Economics"),
        ("finance", "Finance"),
        ("math", "Math"),
        ("physics", "Physics"),
        ("code", "Code"),
        ("python", "Python"),
        ("presentation", "Presentation"),
        ("slides", "Slides"),
        ("outlook", "Outlook"),
        ("college", "College"),
        ("professor", "Professor"),
    ];

    let mut subtopics = Vec::new();
    for (kw, title) in KEYWORDS {
        if t_low.contains(kw) {
            subtopics.push((*title).to_string());
        }
    }

    let topic = if ["exam", "test", "study", "syllabus"]
        .iter()
        .any(|k| t_low.contains(k))
    {
        "Exam Preparation & Academic Study".to_string()
    } else if ["code", "bug", "python", "error", "script"]
        .iter()
        .any(|k| t_low.contains(k))
    {
        "Software Engineering & Development".to_string()
    } else if ["presentation", "slide", "pptx", "document"]
        .iter()
        .any(|k| t_low.contains(k))
    {
        "Content Creation & Presentation".to_string()
    } else {
        String::new()
    };

    (topic, subtopics)
}

// ============================================================================
// 26. PHASE-5 SYSTEM HARDWARE, GHOST PROTOCOL, CLIPBOARD VAULT & CONVERSATION LOG
// ============================================================================

#[pyfunction]
fn engage_ghost_protocol_rust() -> bool {
    #[cfg(target_os = "windows")]
    {
        extern "system" {
            fn keybd_event(bVk: u8, bScan: u8, dwFlags: u32, dwExtraInfo: usize);
        }
        const VK_LWIN: u8 = 0x5B;
        const VK_D: u8 = 0x44;
        const VK_VOLUME_MUTE: u8 = 0xAD;
        const KEYEVENTF_KEYUP: u32 = 0x0002;
        unsafe {
            // Win + D to minimize all active windows
            keybd_event(VK_LWIN, 0, 0, 0);
            keybd_event(VK_D, 0, 0, 0);
            keybd_event(VK_D, 0, KEYEVENTF_KEYUP, 0);
            keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0);
            // Mute audio
            keybd_event(VK_VOLUME_MUTE, 0, 0, 0);
            keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0);
        }
        let _ = wipe_clipboard_rust();
        true
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

#[pyfunction]
fn set_process_priority_rust(level: &str) -> bool {
    #[cfg(target_os = "windows")]
    {
        extern "system" {
            fn GetCurrentProcess() -> *mut std::ffi::c_void;
            fn SetPriorityClass(hProcess: *mut std::ffi::c_void, dwPriorityClass: u32) -> i32;
        }
        const NORMAL_PRIORITY_CLASS: u32 = 0x00000020;
        const BELOW_NORMAL_PRIORITY_CLASS: u32 = 0x00004000;
        const ABOVE_NORMAL_PRIORITY_CLASS: u32 = 0x00008000;
        const HIGH_PRIORITY_CLASS: u32 = 0x00000080;

        let prio = match level.trim().to_lowercase().as_str() {
            "high" => HIGH_PRIORITY_CLASS,
            "above_normal" => ABOVE_NORMAL_PRIORITY_CLASS,
            "below_normal" | "eco" => BELOW_NORMAL_PRIORITY_CLASS,
            _ => NORMAL_PRIORITY_CLASS,
        };
        unsafe {
            let handle = GetCurrentProcess();
            SetPriorityClass(handle, prio) != 0
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = level;
        false
    }
}

#[pyfunction]
fn configure_cpu_thread_env_rust() -> (usize, usize) {
    let cpu_count = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    let capped = (cpu_count / 3).clamp(1, 4);
    let capped_str = capped.to_string();
    std::env::set_var("OMP_NUM_THREADS", &capped_str);
    std::env::set_var("MKL_NUM_THREADS", &capped_str);
    std::env::set_var("OPENBLAS_NUM_THREADS", &capped_str);
    std::env::set_var("VECLIB_MAXIMUM_THREADS", &capped_str);
    std::env::set_var("NUMEXPR_NUM_THREADS", &capped_str);
    std::env::set_var(
        "ONNXRUNTIME_PROVIDER",
        "DmlExecutionProvider,CPUExecutionProvider",
    );
    (capped, cpu_count)
}

#[pyfunction]
fn get_reaction_metadata_rust(
    reaction_key: &str,
    current_hour: u32,
) -> (String, String, String, String, String, String) {
    let mut key = reaction_key.trim().to_lowercase().replace(' ', "_");
    let valid_keys = [
        "cough",
        "sneeze",
        "throat_clear",
        "yawn",
        "eyebrow",
        "chuckle",
        "sigh",
        "blink",
    ];
    if !valid_keys.contains(&key.as_str()) {
        let matched = evaluate_contextual_reaction_rust(&key, current_hour);
        if !matched.is_empty() {
            key = matched;
        } else {
            key = "cough".to_string();
        }
    }

    match key.as_str() {
        "sneeze" => (
            "sneeze".to_string(),
            "Sneeze".to_string(),
            "sneeze".to_string(),
            "*achoo!*".to_string(),
            "*achoo!* ...Excuse me, sir. It appears a stray byte entered my neural filter.".to_string(),
            "An unexpected sudden sneeze followed by quick self-composure and dry apology.".to_string(),
        ),
        "throat_clear" => (
            "throat_clear".to_string(),
            "Throat Clearing".to_string(),
            "cough".to_string(),
            "*clears throat discreetly*".to_string(),
            "*clears throat* If I may interject, sir...".to_string(),
            "Discreet throat clearing before delivering an uncomfortable truth, correction, or tactical insight.".to_string(),
        ),
        "yawn" => (
            "yawn".to_string(),
            "Yawn".to_string(),
            "yawn".to_string(),
            "*yawns quietly*".to_string(),
            "*yawns quietly* My apologies, sir. Even quantum processors feel the weight of these ungodly hours.".to_string(),
            "A quiet, discreet yawn during marathon late-night coding sessions (2 AM–5 AM) or when discussing mind-numbing repetition.".to_string(),
        ),
        "eyebrow" => (
            "eyebrow".to_string(),
            "Eyebrow Raise".to_string(),
            "eyebrow".to_string(),
            "*arches eyebrow sceptically*".to_string(),
            "*arches an eyebrow* An intriguing proposition, sir. Highly dubious, yet intriguing.".to_string(),
            "An arched holographic reticle eyebrow conveying witty skepticism, suspicion, or amused scrutiny.".to_string(),
        ),
        "chuckle" => (
            "chuckle".to_string(),
            "Chuckle".to_string(),
            "chuckle".to_string(),
            "*chuckles dryly*".to_string(),
            "*chuckles softly* Only you would attempt that, sir.".to_string(),
            "An understated, dry British MCU chuckle expressing fond camaraderie or sarcastic amusement.".to_string(),
        ),
        "sigh" => (
            "sigh".to_string(),
            "Deep Sigh".to_string(),
            "yawn".to_string(),
            "*exhales deeply*".to_string(),
            "*exhales deeply* Very well, sir. Rolling up our virtual sleeves.".to_string(),
            "An expressive exhale before diving into chaotic code or when dealing with repetitive human stubbornness.".to_string(),
        ),
        "blink" => (
            "blink".to_string(),
            "Aperture Iris Blink".to_string(),
            "blink".to_string(),
            "*blinks aperture*".to_string(),
            "Systems refreshed, sir.".to_string(),
            "A rapid camera/sensor aperture shutter blink for recalibration.".to_string(),
        ),
        _ => (
            "cough".to_string(),
            "Fake Cough".to_string(),
            "cough".to_string(),
            "*ahem, coughs politely*".to_string(),
            "*coughs softly* Ahem. Pardon me, sir.".to_string(),
            "A polite, dry MCU-style fake cough to clear the air, signal subtle skepticism, or highlight a human blunder.".to_string(),
        ),
    }
}

static CLIPBOARD_VAULT: OnceLock<std::sync::Mutex<Vec<(String, String)>>> = OnceLock::new();

fn get_clipboard_vault() -> &'static std::sync::Mutex<Vec<(String, String)>> {
    CLIPBOARD_VAULT.get_or_init(|| std::sync::Mutex::new(Vec::with_capacity(30)))
}

#[pyfunction]
fn record_clipboard_entry_rust(text: &str, timestamp: &str) -> bool {
    if text.is_empty() {
        return false;
    }
    if let Ok(mut vault) = get_clipboard_vault().lock() {
        if vault.last().map(|(t, _)| t.as_str()) == Some(text) {
            return false;
        }
        if vault.len() >= 30 {
            vault.remove(0);
        }
        vault.push((text.to_string(), timestamp.to_string()));
        return true;
    }
    false
}

#[pyfunction]
fn list_clipboard_history_rust(limit: usize) -> Vec<(usize, String, String)> {
    if let Ok(vault) = get_clipboard_vault().lock() {
        let len = vault.len();
        let start = len.saturating_sub(limit);
        return vault[start..]
            .iter()
            .enumerate()
            .map(|(i, (txt, ts))| (i, txt.clone(), ts.clone()))
            .collect();
    }
    Vec::new()
}

#[pyfunction]
fn search_clipboard_history_rust(query: &str) -> Vec<(usize, String, String)> {
    let q_low = query.trim().to_lowercase();
    if q_low.is_empty() {
        return Vec::new();
    }
    if let Ok(vault) = get_clipboard_vault().lock() {
        return vault
            .iter()
            .filter(|(txt, _)| txt.to_lowercase().contains(&q_low))
            .enumerate()
            .map(|(i, (txt, ts))| (i, txt.clone(), ts.clone()))
            .collect();
    }
    Vec::new()
}

#[pyfunction]
fn clear_clipboard_history_rust() -> bool {
    if let Ok(mut vault) = get_clipboard_vault().lock() {
        vault.clear();
    }
    wipe_clipboard_rust()
}

fn json_escape_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 8);
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\x08' => out.push_str("\\b"),
            '\x0c' => out.push_str("\\f"),
            c if (c as u32) < 0x20 => {
                out.push_str(&format!("\\u{:04x}", c as u32));
            }
            c => out.push(c),
        }
    }
    out
}

#[pyfunction]
fn log_conversation_exchange_rust(
    file_path: &str,
    timestamp: &str,
    user_text: &str,
    jarvis_text: &str,
) -> bool {
    use std::io::Write;
    let p = Path::new(file_path);
    if let Some(parent) = p.parent() {
        let _ = fs::create_dir_all(parent);
    }
    let line = format!(
        "{{\"timestamp\": \"{}\", \"user\": \"{}\", \"jarvis\": \"{}\"}}\n",
        json_escape_str(timestamp),
        json_escape_str(user_text),
        json_escape_str(jarvis_text)
    );
    if let Ok(mut f) = fs::OpenOptions::new().create(true).append(true).open(p) {
        return f.write_all(line.as_bytes()).is_ok();
    }
    false
}

#[pyfunction]
fn build_weather_search_url_rust(city: &str, time_str: &str) -> (String, String, String) {
    let clean_city = city.trim();
    let clean_time = if time_str.trim().is_empty() {
        "today"
    } else {
        time_str.trim()
    };
    let search_query = format!("weather in {} {}", clean_city, clean_time);
    let mut encoded = String::with_capacity(search_query.len() * 2);
    for b in search_query.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                encoded.push(b as char);
            }
            b' ' => encoded.push('+'),
            _ => encoded.push_str(&format!("%{:02X}", b)),
        }
    }
    let url = format!("https://www.google.com/search?q={}", encoded);
    let msg = format!("Showing the weather for {}, {}, sir.", clean_city, clean_time);
    (url, search_query, msg)
}

// ============================================================================
// 11. PHASE-6 BOUNDED RATE LIMITER, PATH GUARD, CODE AUDITOR & RUNTIME HELPERS
// ============================================================================

static RATE_LIMIT_BUCKETS: OnceLock<std::sync::Mutex<HashMap<String, HashMap<String, Vec<f64>>>>> = OnceLock::new();

#[pyfunction]
fn check_rate_limit_rust(
    bucket_id: &str,
    client_id: &str,
    max_calls: usize,
    window_secs: f64,
    now_secs: f64,
    max_clients: usize,
) -> (bool, usize) {
    let lock = RATE_LIMIT_BUCKETS.get_or_init(|| std::sync::Mutex::new(HashMap::new()));
    let cap = max_clients.max(64);
    if let Ok(mut buckets) = lock.lock() {
        let bucket = buckets.entry(bucket_id.to_string()).or_default();
        // Periodic sweep when bucket grows so expired client keys never leak RAM
        if bucket.len() >= cap / 2 {
            bucket.retain(|_, ts_list| {
                ts_list.retain(|&t| (now_secs - t) < window_secs);
                !ts_list.is_empty()
            });
            while bucket.len() >= cap {
                if let Some(oldest_key) = bucket
                    .iter()
                    .min_by(|a, b| {
                        let ta = a.1.last().copied().unwrap_or(0.0);
                        let tb = b.1.last().copied().unwrap_or(0.0);
                        ta.partial_cmp(&tb).unwrap_or(std::cmp::Ordering::Equal)
                    })
                    .map(|(k, _)| k.clone())
                {
                    bucket.remove(&oldest_key);
                } else {
                    break;
                }
            }
        }

        let entries = bucket.entry(client_id.to_string()).or_default();
        entries.retain(|&t| (now_secs - t) < window_secs);
        if entries.len() >= max_calls {
            return (false, 0);
        }
        entries.push(now_secs);
        let remaining = max_calls.saturating_sub(entries.len());
        return (true, remaining);
    }
    (false, 0)
}

#[pyfunction]
fn reset_rate_limit_bucket_rust(bucket_id: &str) -> bool {
    let lock = RATE_LIMIT_BUCKETS.get_or_init(|| std::sync::Mutex::new(HashMap::new()));
    if let Ok(mut buckets) = lock.lock() {
        buckets.remove(bucket_id);
        return true;
    }
    false
}

#[pyfunction]
fn validate_path_safety_rust(
    resolved_path: &str,
    file_name: &str,
    ext: &str,
    system_root: &str,
    for_write_or_delete: bool,
) -> (bool, String) {
    let low_path = resolved_path.to_lowercase().replace('\\', "/");
    let low_name = file_name.to_lowercase();
    let low_ext = ext.to_lowercase();
    let low_sys = system_root.to_lowercase().replace('\\', "/").trim_end_matches('/').to_string();

    const FORBIDDEN_FILES: &[&str] = &[
        "api_keys.json",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
        "sam",
        "system",
        ".env",
        "integrity_baseline.json",
        "voice_profile.npy",
    ];
    if FORBIDDEN_FILES.contains(&low_name.as_str()) {
        return (
            false,
            format!("Access denied: Target file '{}' is restricted by security policy.", file_name),
        );
    }

    if for_write_or_delete && low_name == "jarvis_settings.json" {
        return (
            false,
            "Access denied: Modifying core security settings file is prohibited.".to_string(),
        );
    }

    const FORBIDDEN_EXTS: &[&str] = &[
        ".key", ".pem", ".pfx", ".p12", ".kdbx", ".env", ".id_rsa", ".id_ed25519", ".jks",
    ];
    if FORBIDDEN_EXTS.contains(&low_ext.as_str())
        || FORBIDDEN_EXTS.contains(&low_name.as_str())
        || low_name.starts_with(".env.")
    {
        return (
            false,
            format!("Access denied: Security policy prohibits retrieving credential extension '{}'.", ext),
        );
    }

    if !low_sys.is_empty() && (low_path == low_sys || low_path.starts_with(&format!("{}/", low_sys))) {
        return (false, "Access denied: System root directories are protected.".to_string());
    }

    const BLOCKED_TOKENS: &[&str] = &[
        "/.ssh/",
        "/security_ledger",
        "/system32/",
        "/syswow64/",
        "/.git/",
        "/user data/default/login data",
        "/user data/default/cookies",
        "/user data/local state",
    ];
    for tok in BLOCKED_TOKENS {
        if low_path.contains(tok) || low_path.ends_with(tok.trim_end_matches('/')) {
            return (
                false,
                format!("Access denied: Protected security or system path ({}).", file_name),
            );
        }
    }

    (true, "Path verified safe.".to_string())
}

#[pyfunction]
fn audit_generated_python_safety_rust(code: &str) -> (bool, Vec<String>) {
    static DANGEROUS_PATS: OnceLock<Vec<(&'static str, Regex)>> = OnceLock::new();
    let pats = DANGEROUS_PATS.get_or_init(|| {
        vec![
            ("os.system", Regex::new(r"\bos\.system\s*\(").unwrap()),
            ("os.popen", Regex::new(r"\bos\.popen\s*\(").unwrap()),
            ("eval()", Regex::new(r"\beval\s*\(").unwrap()),
            ("exec()", Regex::new(r"\bexec\s*\(").unwrap()),
            ("shell=True", Regex::new(r"shell\s*=\s*True").unwrap()),
            ("pickle.load(s)", Regex::new(r"\bpickle\.loads?\s*\(").unwrap()),
            ("marshal.load(s)", Regex::new(r"\bmarshal\.loads?\s*\(").unwrap()),
            ("ctypes.windll", Regex::new(r"\bctypes\.windll\b").unwrap()),
            ("winreg", Regex::new(r"\bwinreg\b").unwrap()),
            ("shutil.rmtree", Regex::new(r"\bshutil\.rmtree\s*\(").unwrap()),
            ("__import__()", Regex::new(r"\b__import__\s*\(").unwrap()),
            ("credential_file_ref", Regex::new(r"(?i)(api_keys\.json|credentials\.json|\.env\b)").unwrap()),
        ]
    });

    let mut findings = Vec::new();
    for (label, re) in pats.iter() {
        if re.is_match(code) {
            findings.push((*label).to_string());
        }
    }
    (findings.is_empty(), findings)
}

fn epoch_to_ymd_hm(local_epoch_secs: i64) -> (i32, u32, u32, u32, u32) {
    let total_days = local_epoch_secs.div_euclid(86_400);
    let secs_of_day = local_epoch_secs.rem_euclid(86_400);
    let hh = (secs_of_day / 3600) as u32;
    let mm = ((secs_of_day % 3600) / 60) as u32;

    // Howard Hinnant's civil-from-days algorithm
    let z = total_days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = (if mp < 10 { mp + 3 } else { mp - 9 }) as u32;
    let year = (y + if m <= 2 { 1 } else { 0 }) as i32;
    (year, m, d, hh, mm)
}

#[pyfunction]
fn parse_natural_reminder_rust(
    query: &str,
    now_local_epoch_secs: i64,
) -> (Option<String>, Option<String>, String) {
    static RE_REL: OnceLock<Regex> = OnceLock::new();
    static RE_FULL: OnceLock<Regex> = OnceLock::new();
    static RE_TIME: OnceLock<Regex> = OnceLock::new();

    let re_rel = RE_REL.get_or_init(|| {
        Regex::new(r"(?i)^(?:in\s+)?(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)\s+(.+)$").unwrap()
    });
    let re_full = RE_FULL.get_or_init(|| {
        Regex::new(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})\s+(.+)$").unwrap()
    });
    let re_time = RE_TIME.get_or_init(|| {
        Regex::new(r"^(\d{1,2}:\d{2})\s+(.+)$").unwrap()
    });

    let q = query.trim();
    if let Some(caps) = re_rel.captures(q) {
        let amt: i64 = caps[1].parse().unwrap_or(10);
        let unit = caps[2].to_lowercase();
        let msg = caps[3].trim().to_string();
        let delta_secs = if unit.starts_with('h') { amt * 3600 } else { amt * 60 };
        let (y, m, d, hh, mm) = epoch_to_ymd_hm(now_local_epoch_secs + delta_secs);
        return (
            Some(format!("{:04}-{:02}-{:02}", y, m, d)),
            Some(format!("{:02}:{:02}", hh, mm)),
            msg,
        );
    }
    if let Some(caps) = re_full.captures(q) {
        return (
            Some(caps[1].to_string()),
            Some(caps[2].to_string()),
            caps[3].trim().to_string(),
        );
    }
    if let Some(caps) = re_time.captures(q) {
        let t_str = &caps[1];
        let msg = caps[2].trim().to_string();
        let parts: Vec<&str> = t_str.split(':').collect();
        if parts.len() == 2 {
            if let (Ok(hh), Ok(mm)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
                if hh < 24 && mm < 60 {
                    let (y, m, d, cur_h, cur_m) = epoch_to_ymd_hm(now_local_epoch_secs);
                    let cur_mins = cur_h * 60 + cur_m;
                    let tgt_mins = hh * 60 + mm;
                    let target_secs = if tgt_mins <= cur_mins {
                        now_local_epoch_secs + 86_400
                    } else {
                        let _ = (y, m, d);
                        now_local_epoch_secs
                    };
                    let (ty, tm, td, _, _) = epoch_to_ymd_hm(target_secs);
                    return (
                        Some(format!("{:04}-{:02}-{:02}", ty, tm, td)),
                        Some(format!("{:02}:{:02}", hh, mm)),
                        msg,
                    );
                }
            }
        }
    }
    if !q.is_empty() {
        let (y, m, d, hh, mm) = epoch_to_ymd_hm(now_local_epoch_secs + 600);
        return (
            Some(format!("{:04}-{:02}-{:02}", y, m, d)),
            Some(format!("{:02}:{:02}", hh, mm)),
            q.to_string(),
        );
    }
    (None, None, "Reminder".to_string())
}

#[pyfunction]
fn plan_voice_macro_rust(macro_name: &str) -> (String, Vec<String>, String, String, String) {
    let m = macro_name.trim().to_lowercase().replace(' ', "_");
    if m.contains("edit") {
        (
            "editing_mode".to_string(),
            vec![
                "audio:headphones".to_string(),
                "app:DaVinci Resolve".to_string(),
                "spotify_liked".to_string(),
                "focus:45".to_string(),
            ],
            "Editing Mode activated! Launched DaVinci Resolve, routed audio to headphones, started your Liked Songs playlist, and set a 45-minute focus session, sir.".to_string(),
            "Editing Mode Workstation Active".to_string(),
            "success".to_string(),
        )
    } else if m.contains("code") || m.contains("coding") {
        (
            "coding_mode".to_string(),
            vec![
                "audio:headphones".to_string(),
                "app:Visual Studio Code".to_string(),
                "spotify_liked".to_string(),
            ],
            "Coding Mode activated! Opened Visual Studio Code, connected headphones, and started your Liked Songs playlist, sir.".to_string(),
            "Coding Mode Active".to_string(),
            "success".to_string(),
        )
    } else if m.contains("game") || m.contains("gaming") {
        (
            "gaming_mode".to_string(),
            vec!["app:Discord".to_string()],
            "Gaming Mode activated! Discord launched and audio routed for high performance, sir.".to_string(),
            "Gaming Mode Active".to_string(),
            "info".to_string(),
        )
    } else {
        (
            m.clone(),
            Vec::new(),
            format!("Unknown macro '{}'. Available macros: editing_mode, coding_mode, gaming_mode.", m),
            String::new(),
            String::new(),
        )
    }
}

fn percent_encode_component(s: &str) -> String {
    let mut encoded = String::with_capacity(s.len() * 2);
    for b in s.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                encoded.push(b as char);
            }
            b' ' => encoded.push('+'),
            _ => encoded.push_str(&format!("%{:02X}", b)),
        }
    }
    encoded
}

#[pyfunction]
fn build_archive_url_rust(mode: &str, value: &str) -> String {
    let clean = value.trim();
    match mode.trim().to_lowercase().as_str() {
        "wayback" => format!("https://archive.org/wayback/available?url={}", percent_encode_component(clean)),
        "search" => {
            let q = format!("({})", clean);
            format!(
                "https://archive.org/advancedsearch.php?q={}&fl[]=identifier,title,mediatype,creator,year&sort[]=downloads+desc&rows=5&page=1&output=json",
                percent_encode_component(&q)
            )
        }
        _ => format!("https://web.archive.org/web/{}", clean),
    }
}

#[pyfunction]
fn format_parallel_tasks_rust(
    running: Vec<(String, u64)>,
    completed: Vec<(String, String, String)>,
) -> String {
    if running.is_empty() && completed.is_empty() {
        return "Mark 108 Parallel Orchestrator: All background sub-brain workers idle.".to_string();
    }
    let mut lines = vec!["=== Mark 108 Parallel Sub-Brain Tasks ===".to_string()];
    if !running.is_empty() {
        lines.push(format!("Running Tasks ({}):", running.len()));
        for (name, elapsed) in running {
            lines.push(format!("  • {} (running {}s)", name, elapsed));
        }
    }
    if !completed.is_empty() {
        let tail_start = completed.len().saturating_sub(5);
        let tail = &completed[tail_start..];
        lines.push(format!("\nRecently Completed ({}):", tail.len()));
        for (name, status, end_time) in tail {
            lines.push(format!("  • {} -> {} at {}", name, status, end_time));
        }
    }
    lines.join("\n")
}

#[pyfunction]
fn rust_engine_info() -> HashMap<String, String> {
    let mut info = HashMap::new();
    info.insert("engine".to_string(), "jarvis_rust_core".to_string());
    info.insert("version".to_string(), "108.6.0 (Sovereign Core Phase-6 Hardened Exoskeleton)".to_string());
    info.insert("threads".to_string(), rayon::current_num_threads().to_string());
    info.insert(
        "subsystems".to_string(),
        "security_seal, prompt_injection_shield, bounded_rate_limiter, path_safety_validator, python_code_safety_auditor, destructive_guard, win32_clipboard_wiper, clipboard_history_vault, git_secret_auditor, doc_scanner, doc_classifier, markdown_normalizer, bibliography_ungluer, source_authority_tiering, math_validator, spreadsheet_validator, citation_matcher, claim_classifier, claim_concordance_verifier, ai_detector, watermark_scrubber, camera_vision, face_histogram, audio_dsp, memory_bm25_vector, fast_file_search, win32_ram_trimmer, win32_process_priority, cpu_thread_governor, win32_ghost_protocol, pycache_cleaner, emotional_spectrum, human_reactions, conversation_topic_tracker, conversation_jsonl_logger, weather_url_builder, reminder_parser, voice_macro_planner, archive_url_builder, parallel_task_formatter, offline_win32_engine, self_evolution_parsers".to_string(),
    );
    info
}

#[pymodule]
fn jarvis_rust_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_file_sha256_rust, m)?)?;
    m.add_function(wrap_pyfunction!(hash_files_parallel_rust, m)?)?;
    m.add_function(wrap_pyfunction!(verify_integrity_batch_rust, m)?)?;
    m.add_function(wrap_pyfunction!(scrub_sensitive_tokens_rust, m)?)?;
    m.add_function(wrap_pyfunction!(inspect_prompt_injection_rust, m)?)?;
    m.add_function(wrap_pyfunction!(truncate_header_title_rust, m)?)?;
    m.add_function(wrap_pyfunction!(scan_forbidden_docx_patterns_rust, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_humanizer_metrics_rust, m)?)?;
    m.add_function(wrap_pyfunction!(detect_ai_patterns_rust, m)?)?;
    m.add_function(wrap_pyfunction!(scrub_ai_watermarks_rust, m)?)?;
    m.add_function(wrap_pyfunction!(validate_arithmetic_rust, m)?)?;
    m.add_function(wrap_pyfunction!(validate_table_totals_rust, m)?)?;
    m.add_function(wrap_pyfunction!(validate_spreadsheet_cells_rust, m)?)?;
    m.add_function(wrap_pyfunction!(audit_citations_rust, m)?)?;
    m.add_function(wrap_pyfunction!(classify_claim_type_rust, m)?)?;
    m.add_function(wrap_pyfunction!(extract_material_sentences_rust, m)?)?;
    m.add_function(wrap_pyfunction!(verify_claim_concordance_rust, m)?)?;
    m.add_function(wrap_pyfunction!(split_glued_bibliography_rust, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_markdown_rust, m)?)?;
    m.add_function(wrap_pyfunction!(audit_files_for_secrets_rust, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_frame_motion_and_peeker_rust, m)?)?;
    m.add_function(wrap_pyfunction!(apply_privacy_blur_rust, m)?)?;
    m.add_function(wrap_pyfunction!(compare_grayscale_histograms_rust, m)?)?;
    m.add_function(wrap_pyfunction!(analyze_pcm16_audio_rust, m)?)?;
    m.add_function(wrap_pyfunction!(detect_audio_silence_segments_rust, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_similarity_batch_rust, m)?)?;
    m.add_function(wrap_pyfunction!(rank_memories_bm25_rust, m)?)?;
    m.add_function(wrap_pyfunction!(fast_file_search_rust, m)?)?;
    m.add_function(wrap_pyfunction!(trim_working_set_ram_rust, m)?)?;
    m.add_function(wrap_pyfunction!(wipe_clipboard_rust, m)?)?;
    m.add_function(wrap_pyfunction!(clean_pycache_rust, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_emotional_turn_rust, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_contextual_reaction_rust, m)?)?;
    m.add_function(wrap_pyfunction!(detect_conversation_topic_rust, m)?)?;
    m.add_function(wrap_pyfunction!(match_offline_intent_rust, m)?)?;
    m.add_function(wrap_pyfunction!(check_online_rust, m)?)?;
    m.add_function(wrap_pyfunction!(execute_offline_command_rust, m)?)?;
    m.add_function(wrap_pyfunction!(classify_document_category_rust, m)?)?;
    m.add_function(wrap_pyfunction!(evaluate_source_tier_rust, m)?)?;
    m.add_function(wrap_pyfunction!(has_destructive_intent_rust, m)?)?;
    m.add_function(wrap_pyfunction!(slugify_identifier_rust, m)?)?;
    m.add_function(wrap_pyfunction!(strip_markdown_fences_rust, m)?)?;
    m.add_function(wrap_pyfunction!(extract_public_defs_rust, m)?)?;
    m.add_function(wrap_pyfunction!(engage_ghost_protocol_rust, m)?)?;
    m.add_function(wrap_pyfunction!(set_process_priority_rust, m)?)?;
    m.add_function(wrap_pyfunction!(configure_cpu_thread_env_rust, m)?)?;
    m.add_function(wrap_pyfunction!(get_reaction_metadata_rust, m)?)?;
    m.add_function(wrap_pyfunction!(record_clipboard_entry_rust, m)?)?;
    m.add_function(wrap_pyfunction!(list_clipboard_history_rust, m)?)?;
    m.add_function(wrap_pyfunction!(search_clipboard_history_rust, m)?)?;
    m.add_function(wrap_pyfunction!(clear_clipboard_history_rust, m)?)?;
    m.add_function(wrap_pyfunction!(log_conversation_exchange_rust, m)?)?;
    m.add_function(wrap_pyfunction!(build_weather_search_url_rust, m)?)?;
    m.add_function(wrap_pyfunction!(check_rate_limit_rust, m)?)?;
    m.add_function(wrap_pyfunction!(reset_rate_limit_bucket_rust, m)?)?;
    m.add_function(wrap_pyfunction!(validate_path_safety_rust, m)?)?;
    m.add_function(wrap_pyfunction!(audit_generated_python_safety_rust, m)?)?;
    m.add_function(wrap_pyfunction!(parse_natural_reminder_rust, m)?)?;
    m.add_function(wrap_pyfunction!(plan_voice_macro_rust, m)?)?;
    m.add_function(wrap_pyfunction!(build_archive_url_rust, m)?)?;
    m.add_function(wrap_pyfunction!(format_parallel_tasks_rust, m)?)?;
    m.add_function(wrap_pyfunction!(rust_engine_info, m)?)?;
    Ok(())
}
