# Amir's personal site

A small static website: a dashboard homepage, a bookshelf, and a garden of notes. You edit plain files, and `build.py` turns them into the finished site.

## How to edit your website

There are three ways, and they all change the same files:

1. **In your browser with Pages CMS** (easiest, with forms and photo upload). See the next section.
2. **On github.com**: open a file, click the pencil icon, and commit.
3. **On your computer or with Claude Code.**

Every change you commit rebuilds the site automatically in a minute or two.

| I want to... | Edit this |
| --- | --- |
| Change the headline, intro, "Now" panel, cards or tiles on the home page | `site.json` |
| Add my photo | the `photo` field in `site.json`, after uploading the image to `media/` |
| Add a book, change its status, or add a cover photo | `content/books.json` |
| Write a new note | add a file in `content/notes/` (see below) |
| Change the About page | `content/about.md` |
| Add a project | `content/projects.json` |
| Add footer links (GitHub, email, ...) | the `links` list in `site.json` |
| Change colours or fonts | the tokens at the top of `static/style.css` |
| Change the layout or HTML of a page | `build.py` (each page has its own function) |

## Edit from your browser with Pages CMS

[Pages CMS](https://pagescms.org) is a free editor that works directly on this repository. The file `.pages.yml` tells it which forms to show.

1. Go to pagescms.org and sign in with your GitHub account.
2. The first time, GitHub asks you to allow Pages CMS to access your repositories. Allow it for this repository.
3. Open the repository. The sidebar shows **Home page, Books, Notes, Projects, About page** and **Media**.
4. Edit a form, upload photos, and click **Save**. Each save is a commit.
5. Wait about a minute until the **Deploy site** run in the repository's Actions tab shows a green tick. Then refresh your site.

## Photos

Photos live in the `media/` folder. The site resizes them when it builds, so you can upload full-size phone photos.

- **Book covers:** open **Books**, choose a book, and upload a photo of its front cover in the **Photo of the front cover** field. It appears on the home page (for the book you are reading), in the shelf on the Books page, and in the book list. Portrait photos taken straight on work best, because covers are shown with a 2:3 shape and the edges are trimmed to fit.
- **Your photo:** open **Home page** and set **Your photo**. It appears in the "Now" panel on the home page and beside the text on the About page. Add a few words in **Photo description**, and an optional line under your name in **Line under your name**.
- **Photos in notes:** the note editor has an image button, or write `![A short description](/media/photo.jpg)` in the note.
- Use JPG, PNG or WebP files. A photo that is missing or misspelled is skipped, and the site shows a coloured block instead.
- Everything in `media/` is public once you push it, so only upload photos you are happy to share.

Without Pages CMS, add a photo by uploading it to the `media/` folder (on github.com choose **Add file**, then **Upload files**) and putting its path in the file, for example `"cover": "/media/my-book.jpg"`.

### Add a book

Add an entry to `content/books.json`, or use the **Books** form. The `status` is `reading`, `finished` or `want`. A `finished` date (`YYYY-MM-DD`) makes the book appear in the "books finished per month" chart on the home page.

```json
{
  "title": "Book title",
  "author": "Author name",
  "status": "finished",
  "finished": "2026-12-20",
  "cover": "/media/book-title.jpg",
  "takeaway": "One sentence on what I kept from it.",
  "note": "slug-of-a-note-about-it"
}
```

`cover` and `note` are optional. `note` links the book to a file in `content/notes/` (without `.md`).

### Write a note

Use the **Notes** form, or create `content/notes/my-note.md`. The file name becomes the address (`notes/my-note.html`).

```markdown
---
title: What xG does and does not tell you
stage: seedling
tags:
  - football
  - xG
date: 2026-11-20
summary: One sentence that shows under the title.
---

Write in Markdown here. Use ## for section headings.

Link to another note with [[practical-statistics-chapter-3]].
```

- `stage` is `seedling`, `budding` or `evergreen`. Change it as the note grows.
- `date` is the day you last worked on it.
- `tags` can be a list, or one line such as `tags: football, xG`.
- Put quotes around a title that contains a colon, for example `title: "Notes: week one"`.
- Tags create a page for each tag automatically. Linked notes show a "Linked from" list on the other note.

## Preview on your computer

```
pip install -r requirements.txt
python build.py
python -m http.server -d dist
```

Then open http://localhost:8000.

## Publish

Commit and push to the `main` branch. GitHub builds and publishes the site in a minute or two.

```
git add .
git commit -m "Add a new note"
git push
```

## GitHub setup (already done once)

The workflow in `.github/workflows/pages.yml` builds the site and publishes it to GitHub Pages. In the repository's Settings, then Pages, the Source must be **GitHub Actions**. If a run fails, open it in the Actions tab and read the error. On a free GitHub plan, Pages needs a public repository.

## Editing with Claude Code

Open this folder in Claude Code and describe the change in plain words. Good starting prompts:

- "Add a dark mode that follows the visitor's system setting."
- "Add a Football page that lists all notes tagged football, and link it from the home tiles."
- "Make the home page chart show the last 12 months instead of this calendar year."
- "Add an RSS feed for my notes."

Ask it to run `python build.py` and check the result before you push.

## Project layout

```
site.json            home page text, photo, "Now" panel, cards, tiles, footer links
content/
  books.json         the bookshelf
  projects.json      the projects page
  about.md           the About page
  notes/*.md         one file per note
media/               your photos
static/style.css     colours, fonts and all styling
build.py             turns the files above into dist/
.pages.yml           the forms shown by Pages CMS
.github/workflows/   publishes the site when you push
dist/                the generated site (not committed)
```
