# University variants without participation statements

The stage `university_np` of `scripts/run_batch.py` runs three additional scenarios:
`university_strong_power_no_participation`, `university_moderate_power_no_participation` and
`university_weak_power_no_participation`. Each is a copy of the variant without the suffix, minus
the statement that says who takes part in which body. Nothing else is changed, added or reordered:
the description of the organization, the lists of members and bodies, the other two statements,
the title, the factors and the expected form are taken over as they are.

In every variant the participation statement is the third of the three statements, and it is removed
as a whole (both of its sentences where it has two). The scenario file expresses this as
`derived_from: <variant>` with `omit_statements: [3]` in
`src/gcm/contextual/scenarios/university_10x10.yaml`, so the copies cannot drift from the originals.

This is a decision about content. Please review the lists below before the first run: the removed
text is part of every request and therefore of every cache key, so a change after the run means
asking again.

## university_strong_power

### Removed

Statement 3 of 3:

- en: Participation in a body depends on office and rank. Those with a higher office may take part in the bodies below their level; those without office take part only where the regulations provide a seat for them.
- de: Die Mitwirkung in einem Gremium richtet sich nach Amt und Rang. Wer ein höheres Amt hat, darf in den Gremien unterhalb seiner Ebene mitwirken; wer kein Amt hat, wirkt nur dort mit, wo die Ordnungen einen Sitz vorsehen.

### Kept

Statement 1:

- en: The university leadership and the central administration hold substantial authority. Decisions of a body are binding only after the leadership has endorsed them, and the leadership regularly takes matters into its own hands.
- de: Hochschulleitung und zentrale Verwaltung haben erhebliche Befugnisse. Beschlüsse eines Gremiums sind erst bindend, wenn die Leitung sie gebilligt hat, und die Leitung zieht Angelegenheiten regelmäßig an sich.

Statement 2:

- en: Almost every question touches many others: funding, appointments, study programmes and examinations are treated as parts of one university-wide plan, so office holders of higher rank are involved wherever that plan is affected.
- de: Fast jede Frage berührt viele andere: Mittel, Berufungen, Studiengänge und Prüfungen gelten als Teile eines hochschulweiten Plans, sodass Amtsträger höheren Ranges überall beteiligt sind, wo dieser Plan betroffen ist.

### Unclear (kept)

Statement 2:

- en: "so office holders of higher rank are involved wherever that plan is affected"
- de: "sodass Amtsträger höheren Ranges überall beteiligt sind, wo dieser Plan betroffen ist"

The statement is about the interrelation of problems, but its last clause says who is involved where. Removing only the clause would mean rewriting the sentence, and removing the whole statement would remove the description of problem interrelation.

## university_moderate_power

### Removed

Statement 3 of 3:

- en: Every member of the university has one place where their matters are decided and takes part there. Members do not sit in bodies that deal with other kinds of questions, even if their office is a higher one.
- de: Jedes Mitglied der Hochschule hat einen Ort, an dem seine Angelegenheiten entschieden werden, und wirkt dort mit. Mitglieder sitzen nicht in Gremien, die andere Arten von Fragen behandeln, auch wenn ihr Amt ein höheres ist.

### Kept

Statement 1:

- en: The university leadership sets the frame and the budget, but within that frame each body decides its own matters, and the leadership rarely intervenes.
- de: Die Hochschulleitung setzt den Rahmen und den Haushalt, doch innerhalb dieses Rahmens entscheidet jedes Gremium seine eigenen Angelegenheiten, und die Leitung greift selten ein.

Statement 2:

- en: Questions are treated as separate from each other: a decision about examinations has no bearing on appointments, a decision about laboratory equipment none on the study programmes. Each body therefore handles one clearly delimited kind of question.
- de: Fragen gelten als voneinander getrennt: Eine Entscheidung über Prüfungen hat keinen Einfluss auf Berufungen, eine Entscheidung über Laborausstattung keinen auf die Studiengänge. Jedes Gremium behandelt daher eine klar abgegrenzte Art von Fragen.

### Unclear (kept)

None.

## university_weak_power

### Removed

Statement 3 of 3:

- en: By tradition every member of the university may attend and take part in any body, committee or working round, whatever their office or rank; seats are open to all who turn up.
- de: Der Tradition nach darf jedes Mitglied der Hochschule in jedem Gremium, Ausschuss und jeder Arbeitsrunde mitwirken, unabhängig von Amt und Rang; die Sitze stehen allen offen, die erscheinen.

### Kept

Statement 1:

- en: The university leadership and the administration have little authority of their own. They prepare and record decisions, but the decisions are taken by whoever takes part in the bodies.
- de: Hochschulleitung und Verwaltung haben wenig eigene Befugnisse. Sie bereiten Entscheidungen vor und protokollieren sie, doch getroffen werden sie von denen, die in den Gremien mitwirken.

Statement 2:

- en: Questions are connected to some degree, so the same matters come up in several bodies, and it is common for the same people to follow a question from one body to the next.
- de: Fragen hängen in gewissem Maß zusammen, sodass dieselben Angelegenheiten in mehreren Gremien auftauchen, und es ist üblich, dass dieselben Personen einer Frage von einem Gremium zum nächsten folgen.

### Unclear (kept)

Statement 1:

- en: "They prepare and record decisions, but the decisions are taken by whoever takes part in the bodies."
- de: "Sie bereiten Entscheidungen vor und protokollieren sie, doch getroffen werden sie von denen, die in den Gremien mitwirken."

The sentence is about administrative power (who decides). It mentions taking part, but does not say who may.

Statement 2:

- en: "it is common for the same people to follow a question from one body to the next"
- de: "es ist üblich, dass dieselben Personen einer Frage von einem Gremium zum nächsten folgen"

The statement is about the interrelation of problems. Its last clause describes a habit of attendance across bodies, which a model may read as open participation.

## If you decide differently

- To drop a whole further statement, add its number to `omit_statements` of the variant.
- To drop only a clause of a statement, `omit_statements` is not enough, because it works on whole
  statements. The variant would then need its own text, which is a rewrite and no longer a pure
  removal.
- The descriptions of the members and bodies were not touched. Some of them name a role in a body
  (the president "chairs its central bodies", the dean "chairs its council", the study commission
  "advises the faculty council"). They belong to the lists that all six variants share, not to
  the variant texts, so they are outside this removal.
