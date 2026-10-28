# Presentation

Marp deck (`slides.md`) with a custom theme (`theme/hive.css`).

```bash
# live preview: serves this folder, then open http://localhost:8080/slides.md
npx @marp-team/marp-cli@4.1.2 -s . --theme-set theme/hive.css --html --allow-local-files

# export
npx @marp-team/marp-cli@4.1.2 slides.md --theme-set theme/hive.css --html --allow-local-files --pdf
npx @marp-team/marp-cli@4.1.2 slides.md --theme-set theme/hive.css --html --allow-local-files --pptx
```

`--html` is required: the split slide draws its timeline with inline HTML.
In VS Code (Marp extension) add `"markdown.marp.themes": ["./presentation/theme/hive.css"]`
and enable `markdown.marp.enableHtml`.
