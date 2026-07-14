"""
Data engine for the National AI Hub for MNCH — Punjab Mapping (S-22620) dashboard.

Reads the SurveyCTO XLSForm (survey/choices sheets) to build:
 - label maps for every choice list (English)
 - a "question catalogue": every real question, its type, its module/page,
   and — critically — coalesces the EDP (Emergency Delivery Pathway) and
   NDP (Normal Delivery Pathway) variants of the same underlying question
   (e.g. wb1_age_EDP / wb1_age_NDP) into ONE logical variable, so the
   dashboard tells one unified story across both pathways wherever the
   question is conceptually the same, while still allowing pathway-only
   modules (EC, DD, CS, NB, RF, BF ...) to be shown separately.

This file is intentionally data-driven: nothing about specific question
names is hardcoded beyond a few display-label overrides. Re-run tomorrow
with 400 rows instead of 44 and every function below keeps working.
"""

import os
import re
import pandas as pd
import numpy as np

FORM_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), "data", "form.xlsx")
DATA_PATH_DEFAULT = os.path.join(os.path.dirname(__file__), "data", "survey_data.csv")

SYSTEM_TYPES = {
    "start", "end", "today", "deviceid", "subscriberid", "username", "simserial",
    "phonenumber", "caseid", "geopoint", "text audit", "audio audit", "calculate_here",
}

NON_QUESTION_NAME_HINTS = (
    "instr", "n1_", "n_wb", "n_id", "n_interviewer", "hidd_gps", "txt_audit",
    "audio_comp", "c_starttime", "c_startdate", "tt_start", "cal_hour", "sc_instr",
)


def _clean(x):
    if pd.isna(x):
        return None
    x = str(x).strip()
    return x if x and x != "." else None


def strip_pathway(name: str) -> str:
    """Strip trailing _EDP / _NDP (and _EDP2 style) to get the logical variable/group key."""
    return re.sub(r"_(EDP|NDP)\d*$", "", str(name))


def pathway_of(name: str) -> str:
    m = re.search(r"_(EDP|NDP)\d*$", str(name))
    return m.group(1) if m else None


def load_choice_labels(choices_df: pd.DataFrame) -> dict:
    """list_name -> {str(value): label}"""
    maps = {}
    for list_name, grp in choices_df.groupby("list_name"):
        if pd.isna(list_name):
            continue
        d = {}
        for _, row in grp.iterrows():
            val = row.get("value")
            lab = row.get("label:english")
            if pd.isna(val):
                continue
            d[str(val).strip()] = _clean(lab) or str(val)
        maps[str(list_name)] = d
    return maps


def build_group_labels(survey_df: pd.DataFrame) -> dict:
    """group name -> best display label (prefers NDP-context label, falls back to EDP, else prettified name)."""
    labels_by_key = {}
    for _, row in survey_df[survey_df["type"] == "begin group"].iterrows():
        name = _clean(row.get("name"))
        label = _clean(row.get("label:english"))
        if not name:
            continue
        key = strip_pathway(name)
        pw = pathway_of(name)
        if label:
            # Strip "MODULE X: " / "Module X:" prefix noise minimally, keep informative suffix
            display = re.sub(r"^\s*\[?MODULE[\s\-]*[A-Z0-9\-]*:?\]?\s*", "", label, flags=re.I).strip()
            display = re.sub(r"^\s*Module\s+[A-Z0-9\-]+:\s*", "", display, flags=re.I).strip()
            if not display:
                display = label
        else:
            display = None
        prev = labels_by_key.get(key)
        # Prefer NDP-sourced label (broader pathway), then EDP, then any
        if prev is None:
            labels_by_key[key] = {"label": display, "pathway": pw}
        elif display and (prev["label"] is None or (pw == "NDP" and prev["pathway"] != "NDP")):
            labels_by_key[key] = {"label": display, "pathway": pw}
    out = {}
    for key, v in labels_by_key.items():
        out[key] = v["label"] or key.replace("grp_", "").replace("_", " ").title()
    return out


def build_question_catalogue(survey_df: pd.DataFrame, choices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Walk the XLSForm top-to-bottom maintaining a group stack; emit one row per
    real question with: name, type, base_type, list_name, label, module_key,
    module_label, pathway (EDP/NDP/None), var_key (pathway-stripped name).
    """
    group_labels = build_group_labels(survey_df)
    stack = []  # list of (name, key)
    rows = []
    for _, row in survey_df.iterrows():
        t = _clean(row.get("type"))
        name = _clean(row.get("name"))
        if t is None:
            continue
        if t == "begin group" or t == "begin repeat":
            stack.append(strip_pathway(name) if name else None)
            continue
        if t == "end group" or t == "end repeat":
            if stack:
                stack.pop()
            continue
        if name is None:
            continue
        if t in SYSTEM_TYPES:
            continue
        nlow = name.lower()
        if any(h in nlow for h in NON_QUESTION_NAME_HINTS):
            continue
        if t == "select_one read_only":
            continue  # interviewer instruction / warning text, not a real question

        base_type = t.split(" ")[0]  # select_one, select_multiple, integer, decimal, calculate, text, image...
        list_name = t.split(" ", 1)[1] if base_type in ("select_one", "select_multiple") and " " in t else None
        label = _clean(row.get("label:english"))

        # module = outermost group under the pathway root (skip the plain "." groups)
        module_key = None
        for key in stack:
            if key and key not in ("group_EDP_main", "group_NDP_main"):
                module_key = key
                break
        if module_key is None and stack:
            module_key = stack[-1]

        pw = pathway_of(name)
        if pw is None:
            for key in stack:
                if key:
                    pw2 = pathway_of(key)
                    # module keys are already stripped; infer pathway from raw stack instead
            pw = None

        rows.append({
            "name": name,
            "var_key": strip_pathway(name),
            "type": base_type,
            "list_name": list_name,
            "label": label,
            "module_key": module_key,
            "module_label": group_labels.get(module_key, (module_key or "General").replace("_", " ").title()) if module_key else "General",
            "pathway": pathway_of(name),
        })
    return pd.DataFrame(rows)


def infer_pathway_from_stack(survey_df: pd.DataFrame) -> dict:
    """name -> pathway ('EDP'/'NDP'/None) based on ancestor group, since not every leaf name carries the suffix."""
    result = {}
    stack = []
    for _, row in survey_df.iterrows():
        t = _clean(row.get("type"))
        name = _clean(row.get("name"))
        if t is None:
            continue
        if t in ("begin group", "begin repeat"):
            pw = pathway_of(name) if name else None
            stack.append(pw)
            continue
        if t in ("end group", "end repeat"):
            if stack:
                stack.pop()
            continue
        if name is None:
            continue
        pw = pathway_of(name)
        if pw is None:
            for p in reversed(stack):
                if p:
                    pw = p
                    break
        result[name] = pw
    return result


def load_form(form_path: str = FORM_PATH_DEFAULT):
    survey_df = pd.read_excel(form_path, "survey")
    choices_df = pd.read_excel(form_path, "choices")
    catalogue = build_question_catalogue(survey_df, choices_df)
    pathway_map = infer_pathway_from_stack(survey_df)
    catalogue["pathway"] = catalogue.apply(
        lambda r: r["pathway"] or pathway_map.get(r["name"]), axis=1
    )
    label_maps = load_choice_labels(choices_df)
    return catalogue, label_maps


def load_data(data_path: str = DATA_PATH_DEFAULT) -> pd.DataFrame:
    df = pd.read_csv(data_path, low_memory=False)
    return df


def hf_download(repo_id: str, filename: str, token: str, repo_type: str = "dataset") -> str:
    """
    Pull a file from a private Hugging Face Hub dataset repo and return the local
    cached path. `filename` can include a subfolder path within the repo, e.g.
    "s22620-mnch/survey_data.csv" if the data lives in a folder alongside other
    unrelated files in the same dataset repo. hf_hub_download checks the remote
    ETag on every call, so as long as the caller re-invokes this (e.g. on a
    TTL'd st.cache_data), an updated file pushed to HF is picked up automatically.
    """
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo_id=repo_id, filename=filename, repo_type=repo_type, token=token)


def decode_series(series: pd.Series, list_name: str, label_maps: dict) -> pd.Series:
    """Map a select_one column's coded values to English labels."""
    lm = label_maps.get(list_name, {})
    if not lm:
        return series

    def _norm(v):
        s = str(v).strip()
        try:
            f = float(s)
            return str(int(f)) if f.is_integer() else s
        except (ValueError, TypeError):
            return s

    return series.apply(lambda v: lm.get(_norm(v), v) if pd.notna(v) else v)


def coalesce_pathway_columns(data: pd.DataFrame, catalogue: pd.DataFrame) -> pd.DataFrame:
    """
    For every var_key that has BOTH an _EDP and _NDP column present in data,
    create/overwrite a single coalesced column named `var_key` using whichever
    pathway applies to that respondent's `protocol`. Leaves pathway-exclusive
    columns untouched (they simply won't have a counterpart).
    """
    out = data.copy()
    protocol = out.get("protocol")
    grouped = catalogue.groupby("var_key")
    new_cols = {}
    for var_key, grp in grouped:
        if var_key in out.columns:
            continue
        names = grp["name"].unique().tolist()
        present = [n for n in names if n in out.columns]
        if len(present) < 1:
            continue
        edp_col = next((n for n in present if pathway_of(n) == "EDP"), None)
        ndp_col = next((n for n in present if pathway_of(n) == "NDP"), None)
        if edp_col and ndp_col:
            coalesced = out[ndp_col].copy()
            if protocol is not None:
                mask_edp = protocol.astype(str).str.upper() == "EDP"
                coalesced = coalesced.mask(mask_edp, out[edp_col])
            else:
                coalesced = coalesced.combine_first(out[edp_col])
            new_cols[var_key] = coalesced
        elif edp_col or ndp_col:
            # pathway-exclusive question (e.g. EC/CO_E/OC only exist on the EDP arm) —
            # still alias it to var_key so the generic renderer can find it.
            new_cols[var_key] = out[edp_col or ndp_col]
    if new_cols:
        out = pd.concat([out, pd.DataFrame(new_cols, index=out.index)], axis=1)
    return out


def get_select_multiple_frame(data: pd.DataFrame, base_name: str, list_name: str, label_maps: dict) -> pd.DataFrame:
    """Return a tidy 0/1 frame with decoded option labels as columns, for a select_multiple question."""
    opt_cols = [c for c in data.columns if re.match(rf"^{re.escape(base_name)}_\d+$", c)]
    if not opt_cols:
        return pd.DataFrame()
    lm = label_maps.get(list_name, {})
    rename = {}
    for c in opt_cols:
        code = c.split("_")[-1]
        rename[c] = lm.get(code, code)
    sub = data[opt_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    sub = sub.rename(columns=rename)
    return sub


def get_unique_variables(catalogue: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse the catalogue to one row per var_key (in first-seen / XLSForm order),
    merging list_names from all pathway variants that share this var_key so that
    decoding a coalesced EDP+NDP column never mislabels values.
    """
    rows = []
    seen = {}
    order = []
    for _, r in catalogue.iterrows():
        vk = r["var_key"]
        if vk not in seen:
            seen[vk] = {
                "var_key": vk, "type": r["type"], "label": r["label"],
                "module_key": r["module_key"], "module_label": r["module_label"],
                "list_names": set([r["list_name"]]) if r["list_name"] else set(),
                "pathways": set([r["pathway"]]) if r["pathway"] else set(),
                "name_first": r["name"],
            }
            order.append(vk)
        else:
            d = seen[vk]
            if r["list_name"]:
                d["list_names"].add(r["list_name"])
            if r["pathway"]:
                d["pathways"].add(r["pathway"])
            if not d["label"] and r["label"]:
                d["label"] = r["label"]
    for vk in order:
        rows.append(seen[vk])
    return pd.DataFrame(rows)


def merged_label_map(list_names: set, label_maps: dict) -> dict:
    merged = {}
    for ln in list_names:
        merged.update(label_maps.get(ln, {}))
    return merged


MODULE_ORDER_HINTS = [
    "sc", "wm", "wb", "pt", "ma", "cm", "cm2", "cm3", "dd", "cs", "mn", "mn_fr",
    "pu", "pr", "fr_a", "ec", "dl_e", "jo", "jo_e", "fa", "fa_e", "fah",
    "ec_pph", "ec_hdp", "ec_sep", "ec_obl", "ec_ane", "ec_ptb", "ec_nns",
    "co", "co_e", "oc", "nb", "rf", "pn", "pn_fr", "pnc_e", "bf",
    "dr", "dr_a", "dr_b", "dr_c", "dr_d", "dr_e", "dr_e2", "dr_f", "dr_g", "dr_h", "ob",
]
