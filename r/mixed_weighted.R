# Mixed-effects aging model refit in lme4, with and without observation weights.
#
# statsmodels' mixedlm (aging.py) can't weight rows, so a 300-minute season counts
# as much as a 2,500-minute one. lme4 can. This script fits the same model both ways
# and backtests them on the same folds as backtest.py, so the only difference is the weights.
#
# Run after run_sql.py:  Rscript r/mixed_weighted.R
# Writes exports/lme4_backtest.csv and exports/lme4_curves.csv

suppressPackageStartupMessages({
  library(lme4)
  library(splines)
})

panel <- read.csv("data/derived/panel_long.csv")
targets <- 2023:2026

fit <- function(d, weighted) {
  d <- d[d$mp >= 500, ]
  d$age_c <- d$age - 27
  d$w <- if (weighted) d$weight / mean(d$weight) else 1
  lmer(value ~ bs(age, df = 4, Boundary.knots = c(18, 46)) + (1 + age_c | slug),
       data = d, weights = w, control = lmerControl(calc.derivs = FALSE))
}

backtest_rows <- list()
curve_rows <- list()
for (s in sort(unique(panel$stat))) {
  long <- panel[panel$stat == s, ]
  cat(s, "\n")
  for (weighted in c(FALSE, TRUE)) {
    for (t in targets) {
      train <- long[long$season < t, ]
      truth <- long[long$season == t & long$slug %in% long$slug[long$season == t - 1], ]
      truth$age_c <- truth$age - 27
      m <- suppressWarnings(suppressMessages(fit(train, weighted)))
      p <- predict(m, newdata = truth, allow.new.levels = TRUE)
      backtest_rows[[length(backtest_rows) + 1]] <- data.frame(
        stat = s, season = t, model = if (weighted) "lme4_weighted" else "lme4_unweighted",
        rmse = sqrt(weighted.mean((truth$value - p)^2, truth$mp)))
    }
    m <- suppressWarnings(suppressMessages(fit(long, weighted)))
    ages <- data.frame(age = 19:36)
    f <- predict(m, newdata = ages, re.form = NA)
    f27 <- predict(m, newdata = data.frame(age = 27), re.form = NA)
    curve_rows[[length(curve_rows) + 1]] <- data.frame(
      stat = s, age = ages$age, model = if (weighted) "lme4_weighted" else "lme4_unweighted", value = f - f27)
  }
}

write.csv(do.call(rbind, backtest_rows), "exports/lme4_backtest.csv", row.names = FALSE)
write.csv(do.call(rbind, curve_rows), "exports/lme4_curves.csv", row.names = FALSE)
cat("wrote exports/lme4_backtest.csv and exports/lme4_curves.csv\n")
