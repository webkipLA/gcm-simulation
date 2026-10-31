# Literature

The papers the code implements or relies on, kept next to the code so that a port can be
read side by side with its source.

`sources.yaml` lists every work with its DOI or URL, the BibTeX key of the thesis
bibliography and the files of this repository that use it. The PDFs themselves are stored in
`literature/pdf/<key>.pdf` on your own machine only. That folder is git-ignored because most of
the papers are copyrighted by their publishers (several are JSTOR copies for personal use), and
committing them would redistribute them through this public repository.

## Filling the folder

```bash
uv run scripts/sync_literature.py sync --from ~/path/to/your/papers   # copy your existing PDFs
uv run scripts/sync_literature.py download                            # fetch the open-access ones
uv run scripts/sync_literature.py                                     # show what is present
uv run scripts/sync_literature.py which src/gcm/fortran               # sources behind a module
```

`sync` recognises a file by checksum or by name, copies it under its BibTeX key and never
overwrites an existing file unless `--force` is given. `download` only fetches entries with an
`open_pdf` link (arXiv and open-access journals).

## Adding a source

Add an entry to `sources.yaml` with at least `key`, `citation` and `title`, then run `sync` or
put the file into `literature/pdf/` as `<key>.pdf` yourself.
