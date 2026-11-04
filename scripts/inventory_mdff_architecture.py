"""Read-only AST inventory used for the Part 1B consolidation review."""
import ast
import json
import csv
from pathlib import Path


def inventory(root):
    records = []
    for path in sorted((root / 'src/emcd_sim').rglob('*.py')):
        text = path.read_text(encoding='utf-8-sig')
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.get_source_segment(text, node) or ''
            records.append(dict(module=path.relative_to(root).as_posix(),
                function=node.name, line=node.lineno,
                ni_mentions=('ni_' in node.name.lower() or 'nickel' in body.lower()
                             or "'Ni'" in body or '"Ni"' in body),
                decorators=[ast.unparse(d) for d in node.decorator_list]))
    return records


def classification(record):
    """Conservative review dispositions; never infer deletion from references."""
    module=record['module'];name=record['function']
    if module.endswith('/gui/imported_tensor_ui.py') and name=='generate_atomic_tensor':
        return 'D','Historical generation/export callback retained; new GUI uses direct atomic parameters'
    if module.endswith('/historical_ni.py'):
        if name=='ni_local_transitions':return 'C,D','Historical inputs into shared generator with explicit amplitude policy'
        if name=='validate':return 'A,D','Retained Ni physical-input compatibility'
        return 'B,D','Retained shared angular/radial algebra or historical CLI/API'
    if not record['ni_mentions']:return 'general','Retained; no Ni-specific implementation identified'
    if module.endswith('/atomic_ionization.py'):return 'A','Provider-specific 2p-to-3d parameter eligibility; retained'
    if module.endswith(('/benchmark.py','/study_geometry.py','/multislice_reference.py')):
        return 'E','Independent scientific benchmark/reference; retained'
    if module.endswith('/gui/emcd_forward.py') and name=='_calculate':
        return 'C,D','Production body extracted into common forward_pipeline; API retained'
    if module.endswith(('/single_channeling_tensor.py','/double_channeling.py')):
        return 'B,D','Kernel unchanged; explicit generalized sites bypass historical Ni-only default domain'
    if module.endswith(('/gui/results.py','/gui/results_browser.py')):
        return 'B','Provider-derived material labels replace Ni-only display assumptions'
    if module.endswith(('/scattering.py','/elastic_providers.py','/legacy_atomic_factors.py')):
        return 'A,D','Elastic provider compatibility outside this consolidation; unchanged'
    if module.endswith(('/gui/scientific_acceptance.py','/gui/unified_elastic_acceptance.py')):
        return 'E','Independent historical acceptance harness; retained'
    return 'A,D','Historical Ni fixture, source/project/default or geometry compatibility; retained'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    records=inventory(Path(__file__).resolve().parents[1])
    if args.output.suffix=='.csv':
        with args.output.open('w',newline='',encoding='utf-8') as stream:
            writer=csv.writer(stream);writer.writerow(['module','function','line','Ni_reference','classification','disposition'])
            for record in records:
                writer.writerow([record['module'],record['function'],record['line'],record['ni_mentions'],*classification(record)])
    else:
        args.output.write_text(json.dumps(records,indent=2) + '\n',encoding='utf-8')
