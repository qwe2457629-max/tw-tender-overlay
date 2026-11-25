---
name: tw-gov-tender
description: Prepare bid documents for a Taiwan government procurement tender (政府採購／公開招標). Unpacks the tender package, reads the tender sheet (招標單), computes the clarification deadline, builds a LaTeX form-overlay kit that prints vendor data onto the agency's original PDF forms, drafts a document checklist, and guides confirming, printing and post-bid archiving. Use when the user says 開新標案, 新標案, 招標包, 投標文件, 填投標單, 投標表單套印, 聲明書, or gives a tender zip / 案號 to prepare.
---

# 台灣政府採購投標準備（tw-gov-tender）

Help the user prepare bid documents for a Taiwan government tender with the tools in this repository. Reply in Traditional Chinese unless the user writes in another language.

Repository layout (paths relative to the repo root; set `REPO` to where it is cloned):
- `core/overlay-core.tex` — overlay macros (draft / preview / final modes, `?` = unconfirmed).
- `example/` — a complete kit on a fictitious form: `forms.tex` (coordinates), `vendor.tex` (data), `entity/` (bidder data files), `kit.json` (which PDF in a tender package maps to which form).
- `tools/` — `new_tender.py`, `coords.py`, `lines.py`, `render.py`, `itbdiff.py`, `cn_amount.py`.
- `docs/lessons.md` — checklist of common pitfalls. Read it before step 4.

## Hard rules

- **Everything generated is a draft.** A value ending in `?` is unconfirmed and prints red. Only remove `?` or switch to `\draftfalse` when the user confirms that item. Never decide for the user: the bidding entity, prices, declaration answers (聲明書), who signs, who attends.
- **Do not submit, send or upload anything for the user**: no bids, clarification requests (疑義), emails or portal actions. Draft them; the user sends.
- **Keep tender data where the user keeps it.** Do not upload tender files or company data to external services. Background data an agency provides under confidentiality must not be copied into templates, skills or shared libraries.
- **After every change to a form kit, recompile and show the user `preview.pdf`**, with a one-line summary of what changed.
- **Company documents must be re-checked per tender** (registration extract, tax proof, e-receipt, declaration version, signatory authority). Never reuse an old printout without saying so.

## Workflow

1. **Gather inputs**: the tender package (zip or folder), the announcement date (公告日), and which bidder entity file to use. Ask only for what is missing.
2. **Run the script**:
   ```
   python tools/new_tender.py <package.zip> <project folder> --kit <kit folder> --announce YYYY-MM-DD --entity <entity.tex>
   ```
   Verify every printed field against the tender sheet yourself: 案號, deadlines, budget and tax basis, copies, bid bond, venue. The parser reads fixed labels and agencies vary.
3. **Clarification deadline (疑義期限)**: usually one quarter of the bidding period from the announcement date, rounded up. Tell the user the date first; it is often only 4–7 days away.
4. **Write the checklist** `<案號>_投標文件準備清單.md` from the 招標單, 投標須知 and 資格審查單: key dates, what goes in which envelope, special qualifications and who supplies each, evaluation scoring, and a "to confirm" list (entity, foreign documents needing notarised Chinese translations, restrictions on mainland-China involvement, language rules). Check `docs/lessons.md`.
5. **Adapt the kit to the agency's forms**:
   - Copy the agency's forms into `src/` and map them in `kit.json`.
   - Measure field positions with `tools/coords.py` (text baselines) and `tools/lines.py` (table grid lines, character boxes); write `\putl/\putc/\putr`, `\decl`, `\chk`, `\digit` calls in `forms.tex`.
   - Test with dummy data in every field, render with `tools/render.py`, and fix overlaps before using real data.
6. **Fill known facts** from the entity file and what the user gives. Ask the user to confirm each `?`. Amount in Chinese capitals for the bid form: `python tools/cn_amount.py <amount> <cells>`.
7. **Before the deadline**:
   - Re-download the tender package and diff it against the first one (`tools/itbdiff.py`). Packages get amended, and forms can be added or removed.
   - For a foreign-currency bid, compute the break-even exchange rate against the budget.
   - Check the proposal and price documents for consistency: tax wording, discount %, man-days, project name, tender number and date in footers.
8. **Print guidance**: A4 at 100%. List which pages go in which envelope, what is carried on opening day, copies, and who signs and stamps. Remind: check the debarred-vendor list on the submission day; the e-receipt (電子領標憑據) must be collected under the bidding entity's account for this tender.
9. **After the tender**: record the result, new company documents and lessons in the user's library, and add them to `docs/lessons.md`-style notes for next time.
