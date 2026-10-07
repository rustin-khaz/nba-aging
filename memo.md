# Memo: how players age, and who's most at risk in 2026-27

The question: how much does a player change as he gets older, skill by skill, and what should we expect from each player next season?

## 1. The usual aging curve overstates decline

The common method compares each player's season to his next one and averages those changes by age. The problem is that a player only has a "next season" if he stays in the league, and whether he stays depends on how well he just played. So the players still around at 33 are mostly coming off good seasons, and some of those seasons were lucky. The luck wears off the following year, and the common method counts that as aging.

Once I corrected for who stays and who leaves, the average drop from age 27 to 34 came out to 1.9 points of BPM instead of the 2.8 the usual method gives. Late-career decline is real. It's just about a third smaller than the usual method says.

![](docs/img/bpm_curve.png)

## 2. Skills age differently

Shooting holds up. 3P% and FT% stay near their peak into the early 30s.

Players drift away from the basket every year, taking more threes and fewer shots at the rim over their whole careers.

Athletic skills go first. Steals peak around 23, and blocks peak even earlier.

Playmaking, minutes and overall impact peak at 26 or 27. After that they decline slowly, then faster after 32.

Shot-making, meaning how much better a player shoots than his shot locations alone would predict, holds steady until about 32 and then fades, to about 1.4 points below expected by 35. The usual method shows twice that drop.

In practice, that means a 31-year-old shooter will hold on to his main skill longer than a 31-year-old who depends on getting to the rim or making plays on defense.

## 3. Aging risk for 2026-27

Among players 31 and older who played at least 1,500 minutes last season, the biggest projected BPM drops belong to Kawhi Leonard (35), Nikola Jokić (31), Andrew Wiggins (31), Tim Hardaway Jr. (34) and Josh Hart (31). Jokić is still projected to be one of the best players in the league. His drop starts from a very high level, and most of it is an exceptional 2025-26 season coming back toward his multi-year average.

![](docs/img/aging_risk.png)

Every projection comes with an 80% range, and a typical range is about plus or minus 2 BPM, which is wide. I'd use this to rank risk, not as a precise forecast for any one player.

Money changes which of these matter. Looking three seasons out and joining current contracts, Kawhi Leonard stands out: $165M owed through 2028-29 and a projected drop of 3.6 BPM. Kevin Durant ($90M, −2.4) and Jrue Holiday ($72M, −2.0) come next. Jokić's projected drop is similar in size, but he'd still be around 12 BPM, so it isn't a contract problem.

![](docs/img/contract_risk.png)

## 4. How much to trust it

I tested the method on four past seasons (2022-23 through 2025-26), each time using only the data that existed before that season.

It beat "assume he repeats last season" on 10 of 12 skills, with errors 2 to 19% lower.

Its 80% ranges contained the real outcome 78.5% of the time, so the uncertainty estimates hold up.

A more complex statistical model (mixed effects) did worse on every skill, so I didn't use it.

For shot selection (three-point rate and share of shots at the rim), "same as last season" was the best forecast. Players' shot habits barely change from year to year.

Projecting further out is where the correction earns its keep. Three seasons ahead, it cuts the error on minutes by 12% compared to the usual curve, and its 80% ranges still contain the real outcome about 77% of the time.

## 5. Limitations

The correction only accounts for what I can measure: age, performance and minutes. It can't see an injury nobody reported.

BPM is built from box-score stats and misses a lot of defense.

A player who sits out a season gets treated as having left the league.

## 6. What I'd do next

1. Add injury and games-missed data, so a player who didn't come back because he got hurt is treated differently from one who wasn't good enough.
2. Put a plus-minus based impact measure next to BPM, which would cover more of defense.
3. Let the aging curves differ by position or player type, since a rim-running big and a spot-up shooter probably don't age the same way.
