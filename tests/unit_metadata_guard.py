"""Exact approved metadata-label aliases; computational AST remains strict."""
import ast,copy

RECIPROCAL=(
    'Crystallographic g=1/d (Å⁻¹); angular momentum transfer Q=2πg (Å⁻¹). Numerical values unchanged.',
    'g=1/d, Å^-1; legacy cycles/Å values unchanged')
PROJECT_RECIPROCAL=(
    'Å⁻¹; crystallographic g=1/d, angular momentum transfer Q=2πg; numerical values unchanged',
    'Å^-1; crystallographic g=1/d; legacy cycles/angstrom values unchanged')
XMCD=(
    'XMCD-effective; transverse source-maximum normalization; intensity in a.u.',
    'XMCD-effective; transverse source-maximum normalization; relative scattering units')
ATOMIC=(
    'Atomic length-gauge Å²/eV tensor; intensity in a.u.; no absolute cross-section calibration',
    'Atomic length-gauge A^2/eV tensor; relative scattering units; no absolute cross-section calibration')
FALLBACK=('Intensity in a.u.; model-specific normalization','relative research intensity; model-specific normalization')

def alias(node,pair):
    if isinstance(node,ast.Constant) and node.value==pair[0]:node.value=pair[1]

class ApprovedMetadataLabels(ast.NodeTransformer):
    def visit_keyword(self,node):
        self.generic_visit(node)
        if node.arg=='reciprocal_convention':alias(node.value,RECIPROCAL)
        elif node.arg=='reciprocal':alias(node.value,PROJECT_RECIPROCAL)
        elif node.arg=='intensity_convention' and isinstance(node.value,ast.IfExp):
            alias(node.value.body,XMCD);alias(node.value.orelse,ATOMIC)
        elif node.arg=='intensity' and isinstance(node.value,ast.Call):
            c=node.value
            if (isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name)
                    and c.func.value.id=='meta' and c.func.attr=='get' and len(c.args)==2
                    and isinstance(c.args[0],ast.Constant) and c.args[0].value=='intensity_convention'):
                alias(c.args[1],FALLBACK)
        return node

def normalize_unit_metadata(tree):
    return ApprovedMetadataLabels().visit(copy.deepcopy(tree))
