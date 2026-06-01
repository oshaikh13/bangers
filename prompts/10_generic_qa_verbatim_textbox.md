# QA Type: Verbatim Textbox

Generate future-predictive questions whose answer is the exact final text the
user writes into a textbox, composer, prompt field, chat input, comment box,
search box, form field, or similar editable field after `qa_timestamp_ts`.

This QA type is for verbatim text extraction, not paraphrase. Only ask when
future logs make the final text recoverable. The answer must copy the user's
final written text exactly, preserving spelling, casing, punctuation, line
breaks, and typos. Do not summarize, normalize, correct, or quote only part of
the text.

Prefer final text that the user submits, sends, posts, saves, or otherwise
commits. If the user writes in a textbox and then abandons or replaces it, use
the last recoverable textbox contents only when that abandoned final state is
itself useful and clearly visible.

Good questions are short and ask for one final text value:

- "What will the user write in the textbox?"
- "What exact message will the user send next?"
- "What final search query will the user enter?"
- "What exact comment will the user post?"

NO NEED TO PUT THE EXACT TIME IN THE QUESTION - it will be provided.

Do not ask if the future only reveals a general action, a page title, a file
name, a selected option, or an assistant-generated draft. The target text must
be user-authored or user-edited text visible in a textbox-like field.

Use `answer_basis: "F"` or `"H+F"`.

This is a sparse QA type. If there are fewer than `{pairs_per_run}` honestly
recoverable textbox finals, generate fewer pairs. If none are recoverable,
output `"qa_pairs": []`.
