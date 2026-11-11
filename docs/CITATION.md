# Software citation and attribution

[Home](../README.md) · [CITATION.cff](../CITATION.cff) · [BibTeX](../CITATION.bib) · [Scientific references](SCIENTIFIC_REFERENCES.md)

EMCD-Sim is research software developed by **Ding Peng**. The repository owner's public identity and developer's release instructions identify Ding Peng; package author metadata now reflects that identity. The existing MIT copyright notice, “EMCD-Sim contributors,” remains unchanged and does not remove contributor credit.

## Recommended software citation

Peng, D. (2026). *EMCD-Sim: Electron Magnetic Circular Dichroism Simulation Software* (v0.9.0-beta.2) [Computer software]. https://github.com/dingpengem/EMCD-Sim

Use the **actual version used**, or exact source commit for development builds. Windows beta.2 and macOS ARM64 beta.1 binaries have different source commits. Record the packaged build identity. There is no assigned software DOI or claimed peer-reviewed EMCD-Sim software paper.

```bibtex
@software{peng_emcd_sim_2026,
  author = {Peng, Ding},
  title = {{EMCD-Sim}: Electron Magnetic Circular Dichroism Simulation Software},
  year = {2026},
  version = {0.9.0-beta.2},
  url = {https://github.com/dingpengem/EMCD-Sim}
}
```

The root CFF follows [Citation File Format 1.2.0](https://github.com/citation-file-format/citation-file-format/tree/1.2.0); [GitHub's citation feature](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) offers APA and BibTeX. It cites the **software**, rather than substituting a theory paper.

## Source-derived and AI-assisted implementations

If you use EMCD-Sim in your research, please cite the original software in any resulting publications, presentations, or technical reports. This citation request extends to software derived from EMCD-Sim, including forks, modifications, adaptations, ports, source-based reimplementations, and AI-assisted derivative implementations.

Please acknowledge the original source when, for example, you:

- Translate substantial EMCD-Sim code into C++, MATLAB, Julia or another language.
- Use original source files to instruct ChatGPT, OpenAI Codex, GitHub Copilot, Claude or another assistant to rewrite kernels, recreate the GUI, or reimplement substantial code.
- Port the code to another operating system, adapt it into another scientific package, or repackage/extend it with AI assistance.

Using AI coding tools to rewrite, translate, adapt, or regenerate code derived from EMCD-Sim does not eliminate applicable original copyright and license notice obligations. Describe your modifications and cite the original EMCD-Sim version/commit as well as your derivative version.

This is an **academic attribution request**, not a new license restriction or requirement for a separate agreement. The [MIT License](../LICENSE) remains the legal license: applicable copyright and permission notices must accompany copies or substantial portions. Whether particular code is derivative depends on its actual origin and applicable law; AI output is not automatically derivative merely because it looks similar. Independently written software implementing the same published physics is not legally required to cite EMCD-Sim solely for that similarity.

## Software and scientific citations are distinct

Citing the scientific theories and methods underlying EMCD-Sim does not replace citing EMCD-Sim software when it is used. Citing EMCD-Sim does not replace appropriate citation of the original scientific literature. Cite relevant records in the [scientific bibliography](SCIENTIFIC_REFERENCES.md), plus external CIF, MDFF/spectroscopy and elastic-factor data actually used.

For reproducibility report software version/commit, CIF/source, elastic provider, MDFF model/source/scale/validity, magnetization and reversal/frame conventions, BW/MS and Single/Double, beam/potential cutoffs, FFT/slice settings, depth, energy and momentum sampling, and detector geometry. Keep requested uniform-point counts separate from actual evaluated energies. Report approximations and convergence evidence honestly.
