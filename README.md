# Amir's personal site

A small static website: a dashboard homepage, a bookshelf, and a garden of notes. You edit plain files, and `build.py` turns them into the finished site.

## How to edit your website

| I want to... | Edit this |
| --- | --- |
| Change the headline, intro, "Now" panel, cards or tiles on the home page | `site.json` |
| Add a book, change its status, or mark one as finished | `content/books.json` |
| Write a new note | add a file in `content/notes/` (see below) |
| Change the About page | `content/about.md` |
| Add a project | `content/projects.json` |
| Add footer links (GitHub, email, ...) | `links` list in `site.json` |
| Change colours or fonts | the tokens at the top of `static/style.css` |
| Change the layout or HTML of a page | `build.py` (each page has its own function) |

### Add a book

Add an entry to `content/books.json`. The `status` is `reading`, `finished` or `want`. A `finished` date (`YYYY-MM-DD`) makes the book appear in the "books finished per month" chart on the home page.

```json
{
  "title": "Book title",
  "author": "Author name",
  "status": "finished",
  "finished": "2026-12-20",
  "takeaway": "One sentence on what I kept from it.",
  "note": "slug-of-a-note-about-it"
}
```

`note` is optional. It links the book to a file in `content/notes/` (without `.md`).

### Write a note

Create `content/notes/my-note.md`. The file name becomes the address (`notes/my-note.html`).

```markdown
---
title: What xG does and does not tell you
stage: seedling
tags: football, xG
date: 2026-11-20
summary: One sentence that shows under the title.
---

Write in Markdown here. Use ## for section headings.

Link to another note with [[practical-statistics-chapter-3]].
```

- `stage` is `seedling`, `budding` or `evergreen`. Change it as the note grows.
- `date` is the day you last worked on it.
- Tags create a page for each tag automatically. Linked notes show a "Linked from" list on the other note.

### Preview on your computer

```
pip install -r requirements.txt
python build.py
python -m http.server -d dist
```

Then open http://localhost:8000.

### Publish

Commit and push to the `main` branch. GitHub builds and publishes the site in a minute or two.

```
git add .
git commit -m "Add a new note"
git push
```

You can also edit any file directly on github.com (open the file, click the pencil icon, then commit). The site rebuilds the same way.

## One-time GitHub setup

1. Create a new empty repository on github.com (for example `amir-site`, or `yourusername.github.io` for the shortest address).
2. In the project folder run:
   ```
   git remote add origin https://github.com/YOURUSERNAME/REPO.git
   git push -u origin main
   ```
3. On GitHub open the repository, then Settings, then Pages. Under "Build and deployment", set the Source to **GitHub Actions**.
4. Open the Actions tab and wait for "Deploy site" to finish. Your site address is shown in Settings, then Pages.

If the push is rejected because of the workflow file, your access token is missing the `workflow` permission. Create a new token with it, or upload `.github/workflows/pages.yml` through the GitHub website.

## Editing with Claude Code

Open this folder in Claude Code and describe the change in plain words. Good starting prompts:

- "Add a dark mode that follows the visitor's system setting."
- "Add a Football page that lists all notes tagged football, and link it from the home tiles."
- "Make the home page chart show the last 12 months instead of this calendar year."
- "Add an RSS feed for my notes."

Ask it to run `python build.py` and check the result before you push.

## Project layout

```
site.json            home page text, "Now" panel, cards, tiles, footer links
content/
  books.json         the bookshelf
  projects.json      the projects page
  about.md           the About page
  notes/*.md         one file per note
static/style.css     colours, fonts and all styling
build.py             turns the files above into dist/
.github/workflows/   publishes the site when you push
dist/                the generated site (not committed)
```
