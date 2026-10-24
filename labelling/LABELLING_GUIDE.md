# Ground-truth format v2 (what the shortlister actually reads)

One JSON file per resume, saved in `ground_truth_v2/`, named after the PDF (`xyz.pdf` -> `xyz.json`). Copy `TEMPLATE.json` and fill it in.

## Fields
| Field | What to write |
|---|---|
| `resume_file` | PDF file name |
| `candidate_name` | Full name only. No Dr./Prof., no "CV", no degrees after the name |
| `education[]` | HIGHER education only (bachelors and above). Skip 10th/12th/school boards |
| - `degree` | As written in the CV (Ph.D., M.Sc., B.Tech ...) |
| - `degree_level` | `doctorate` / `masters` / `bachelors` / `other` |
| - `stream` | Subject (Computer Science, Physics ...). Empty if the CV doesn't say |
| - `institution` | University / college as written. Empty if missing |
| `experience[]` | Jobs only (what the extractor puts in `experience`). Not teaching lists, not responsibilities, not projects |
| - `job_title` | As written |
| - `institution` | Employer as written |
| - `dates` | Copy EXACTLY as printed ("July 2016 - March 2023", "Since 1st January, 2024"). Never calculate |
| - `experience_type` | `academic` (university, college, research institute) / `industry` (company) / `other` |
| `publications[]` | Every real paper/chapter/book/report. Not talks, workshops attended, or count lines |
| - `title` | Paper title |
| - `type` | `journal` / `conference` / `other` (use the TRUE type, even if the CV heading is wrong) |
| - `year` | 4-digit year, empty if not printed |
| - `venue` | Journal or conference name (empty if not printed) |
| `stated_totals` | Only if the CV prints counts ("Total: 65"). Otherwise leave `null` |
| `notes` | Anything odd. Not scored |

## Rules
- If the CV doesn't say it, leave it empty. Never guess.
- No field is ever calculated: durations, university tiers and publication tiers are computed by the shortlister.
- Check your file with `python validate_gt_v2.py` after each resume.
