import os
import re
import unicodedata


INVALID_FILENAME_CHARS = r'<>:"/\|?*'
KNOWN_SUFFIXES = [
    "-WindowsNoEditor_P",
    "-WindowsNoEditor",
    "_P",
]


def sanitize_filename_component(text: str) -> str:
    text = str(text or "").strip()

    for ch in INVALID_FILENAME_CHARS:
        text = text.replace(ch, "_")

    text = re.sub(r"[\x00-\x1f]", "_", text)
    text = re.sub(r"\s+", " ", text).strip().rstrip(". ")[:120]
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", text, re.I):
        text = "_" + text
    return text or "Skin"


def split_counter_suffix(stem: str):
    """
    Detecta contador final real:
    Nombre(2)
    Nombre (2)

    pero NO toca grupos normales internos.
    """
    match = re.match(r"^(.*?)(?:\s*\((\d+)\))?$", stem)
    if not match:
        return stem, ""

    base = match.group(1) or stem
    counter = match.group(2)

    if counter:
        return base, f"({counter})"

    return base, ""


def split_known_suffix(stem: str):
    """
    Separa el sufijo conocido ANTES del contador.
    Ej:
    Nombre-WindowsNoEditor_P -> Nombre + -WindowsNoEditor_P
    """
    for suffix in KNOWN_SUFFIXES:
        if stem.casefold().endswith(suffix.casefold()):
            return stem[:-len(suffix)], stem[-len(suffix):]
    return stem, ""


def extract_parenthesized_groups(text: str):
    """
    Ej:
    XKing(Cape)(Aweeoppoe)
    -> prefix='XKing', groups=['Cape', 'Aweeoppoe']

    Si no encaja perfectamente, se devuelve todo como prefix.
    """
    start = text.find('(')
    if start < 0:
        return text, []
    prefix, groups = text[:start], []
    index = start
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text[index] != '(':
            return text, []
        depth, end = 1, index + 1
        while end < len(text) and depth:
            depth += (text[end] == '(') - (text[end] == ')')
            end += 1
        if depth:
            return text, []
        groups.append(text[index + 1:end - 1])
        index = end
    return prefix, groups


def normalize_group(group: str) -> str:
    value = unicodedata.normalize('NFKD', str(group or '').casefold())
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return re.sub(r'[\W_]+', ' ', value).strip()


def replace_or_insert_target_skin(
    base_without_suffix: str,
    target_skin_name: str,
    current_skin_display_name: str = "",
    current_skin_internal_name: str = "",
    known_skin_names=(),
):
    """Replace recognized costume groups; preserve the mod prefix and author.

    The last group in a multi-group filename is reserved for author attribution.
    Unrecognized groups are kept rather than guessed to be costume names.
    """
    prefix, groups = extract_parenthesized_groups(base_without_suffix)
    target = sanitize_filename_component(target_skin_name)
    variants = {normalize_group(name) for name in (
        current_skin_display_name, current_skin_internal_name, target, *known_skin_names)}
    variants.discard('')
    removable = [i for i, group in enumerate(groups)
                 if normalize_group(group) in variants and (len(groups) == 1 or i < len(groups) - 1)]
    insert_at = removable[0] if removable else max(0, len(groups) - 1)
    rebuilt = []
    for index, group in enumerate(groups):
        if index == insert_at:
            rebuilt.append(target)
        if index not in removable:
            rebuilt.append(group)
    if not groups:
        return base_without_suffix + '(' + target + ')'
    return prefix + ''.join('(' + group + ')' for group in rebuilt)


def build_output_filename(
    original_mod_path: str,
    target_skin_name: str,
    current_skin_display_name: str = "",
    current_skin_internal_name: str = "",
    known_skin_names=(),
):
    """
    Regla final:
    - preservar el nombre original
    - si detecta la skin actual en el nombre, reemplazarla
    - si no la detecta, insertar la nueva
    - mantener bien el sufijo y el contador
    """
    original_filename = os.path.basename(original_mod_path or "").strip()
    if not original_filename:
        original_filename = "SkinSwap_P.pak"

    stem, ext = os.path.splitext(original_filename)
    ext = ext or ".pak"

    stem_no_counter, counter_suffix = split_counter_suffix(stem)
    body, known_suffix = split_known_suffix(stem_no_counter)

    rebuilt_body = replace_or_insert_target_skin(
        base_without_suffix=body,
        target_skin_name=target_skin_name,
        current_skin_display_name=current_skin_display_name,
        current_skin_internal_name=current_skin_internal_name,
        known_skin_names=known_skin_names,
    )

    final_stem = rebuilt_body + known_suffix + counter_suffix
    final_filename = final_stem + ext

    original_dir = os.path.dirname(original_mod_path)
    if original_dir:
        return os.path.join(original_dir, final_filename)

    return final_filename
