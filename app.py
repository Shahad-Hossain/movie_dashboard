"""Movie ratings dashboard.

Answers four questions about data/movie_ratings.csv (MovieLens 100K joined with
movie and user metadata) and renders one chart per question.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="Movie Ratings Dashboard", page_icon="🎬", layout="wide")

DATA_PATH = Path(__file__).parent / "data" / "movie_ratings.csv"

# --------------------------------------------------------------------------- #
# Theme / palette                                                              #
# --------------------------------------------------------------------------- #
# Chart colors follow a fixed role-based palette. Light and dark values are
# selected separately so marks clear contrast on Streamlit's own surfaces
# (light #ffffff, dark #0e1117); backgrounds are transparent so the chart sits
# on whatever surface Streamlit renders.
PALETTES = {
    "light": dict(
        surface="#ffffff", ink="#0b0b0b", ink2="#52514e", muted="#898781",
        grid="#e1e0d9", axis="#c3c2b7", deemph="#c3c2b7",
        s1="#2a78d6", s2="#eb6834", s1_soft="#9ec5f4",
    ),
    "dark": dict(
        surface="#0e1117", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
        grid="#2c2c2a", axis="#383835", deemph="#52514e",
        s1="#3987e5", s2="#d95926", s1_soft="#256abf",
    ),
}


def current_theme() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:  # older Streamlit or no browser context
        return "light"


P = PALETTES[current_theme()]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def style(fig: go.Figure, height: int = 420) -> go.Figure:
    """Apply the shared chart chrome: transparent surface, hairline grid, muted axis text."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=P["ink2"], size=13),
        margin=dict(l=10, r=20, t=40, b=10),
        height=height,
        hoverlabel=dict(bgcolor=P["surface"], font=dict(color=P["ink"], family=FONT), bordercolor=P["axis"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=P["ink2"])),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=P["grid"], gridwidth=1, zeroline=False, automargin=True,
        showline=False, tickfont=dict(color=P["muted"]), title_font=dict(color=P["muted"]),
    )
    fig.update_yaxes(
        showgrid=False, zeroline=False, showline=False, automargin=True,
        tickfont=dict(color=P["muted"]), title_font=dict(color=P["muted"]),
    )
    return fig


# --------------------------------------------------------------------------- #
# Data                                                                         #
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading ratings…")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["year"] = df["year"].astype("Int64")
    df["decade"] = df["decade"].astype("Int64")
    return df


@st.cache_data
def explode_genres(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (rating, genre). A rating of a 3-genre movie becomes 3 rows."""
    return df.assign(genre=df["genres"].str.split("|")).explode("genre")


df = load_data()
exploded = explode_genres(df)
overall_mean = df["rating"].mean()

# One row per movie (keyed on movie_id; a few titles map to two ids in this dataset).
movies = df.drop_duplicates("movie_id")[["movie_id", "title", "year", "genres"]]
movie_genres = movies.assign(genre=movies["genres"].str.split("|")).explode("genre")

# --------------------------------------------------------------------------- #
# Header                                                                       #
# --------------------------------------------------------------------------- #
st.title("🎬 Movie Ratings Dashboard")
st.caption(
    "Source: `data/movie_ratings.csv` (MovieLens 100K with movie and user metadata). "
    "Ratings are whole numbers from 1 to 5."
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ratings", f"{len(df):,}")
k2.metric("Movies rated", f"{df['movie_id'].nunique():,}")
k3.metric("Users", f"{df['user_id'].nunique():,}")
k4.metric("Overall mean rating", f"{overall_mean:.2f}")

st.divider()

# --------------------------------------------------------------------------- #
# Q1 - Genre breakdown                                                         #
# --------------------------------------------------------------------------- #
st.header("1. Genre breakdown")
st.markdown(
    """
**How multi-genre movies are handled.** Each movie's `genres` field is a
pipe-separated list (for example `Crime|Film-Noir|Mystery|Thriller`). Before
counting anything, that list is **split so the movie appears once under every
genre it carries**. A four-genre movie therefore adds one to four different
genre totals. Two consequences follow:

- the genre totals **add up to more than the number of movies** (or ratings), because
  roughly half of the movies carry more than one genre, and
- no genre is treated as "primary": the first genre listed gets no special weight.

You can count either **distinct movies** (each movie contributes once per genre it
carries, regardless of how often it was rated) or **ratings** (a genre's total is how
many ratings landed on movies tagged with it, so heavily-rated movies weigh more).
"""
)

count_mode = st.radio(
    "Count by",
    ["Distinct movies", "Ratings"],
    horizontal=True,
    help="Distinct movies answers 'how many rated movies are tagged with each genre'. "
    "Ratings answers 'how much of the rating activity touched each genre'.",
)

if count_mode == "Distinct movies":
    genre_counts = movie_genres["genre"].value_counts()
    base_n, base_label = len(movies), "movies"
else:
    genre_counts = exploded["genre"].value_counts()
    base_n, base_label = len(df), "ratings"

genre_counts = genre_counts.sort_values(ascending=True)
share = genre_counts / base_n

multi = (movies["genres"].str.count(r"\|") > 0).sum()
st.caption(
    f"{multi:,} of {len(movies):,} movies ({multi / len(movies):.0%}) carry more than one genre, "
    f"so the bars below sum to {int(genre_counts.sum()):,} tags across {base_n:,} {base_label}. "
    f"Percentages are the share of {base_label} tagged with each genre."
)

top3 = set(genre_counts.nlargest(3).index)
labels = [f"{v:,}  ({share[g]:.0%})" if g in top3 else "" for g, v in genre_counts.items()]

fig1 = go.Figure(
    go.Bar(
        x=genre_counts.values,
        y=genre_counts.index,
        orientation="h",
        marker=dict(color=P["s1"], cornerradius=4),
        text=labels,
        textposition="outside",
        textfont=dict(color=P["ink2"]),
        cliponaxis=False,
        customdata=share.values,
        hovertemplate="<b>%{y}</b><br>%{x:,} " + base_label + " (%{customdata:.1%})<extra></extra>",
    )
)
fig1.update_layout(bargap=0.4, xaxis_title=f"Number of {base_label} tagged with the genre")
fig1.update_xaxes(range=[0, genre_counts.max() * 1.18], tickformat=",")
style(fig1, height=560)
st.plotly_chart(fig1, width="stretch", theme=None)

with st.expander("Table view"):
    t = pd.DataFrame({"Genre": genre_counts.index[::-1], base_label.capitalize(): genre_counts.values[::-1]})
    t["Share"] = (t[base_label.capitalize()] / base_n).map("{:.1%}".format)
    st.dataframe(t, hide_index=True, width="stretch")

st.divider()

# --------------------------------------------------------------------------- #
# Q2 - Genre satisfaction                                                      #
# --------------------------------------------------------------------------- #
st.header("2. Genre satisfaction")
st.markdown(
    "Mean rating per genre, using the same one-row-per-genre split as above. "
    "A rating on a `Comedy|Romance` movie counts toward both genres' means."
)

min_genre_n = st.slider(
    "Minimum number of ratings for a genre to be shown",
    min_value=0, max_value=2000, value=100, step=50,
    help="Genres with very few ratings (the dataset has an 'unknown' genre with 10) give unreliable means.",
)

genre_stats = (
    exploded.groupby("genre")["rating"].agg(mean="mean", n="count").reset_index()
)
hidden = genre_stats[genre_stats["n"] < min_genre_n]
genre_stats = genre_stats[genre_stats["n"] >= min_genre_n].sort_values("mean")

k = 3
lo = set(genre_stats.head(k)["genre"])
hi = set(genre_stats.tail(k)["genre"])

fig2 = go.Figure()
x_min, x_max = genre_stats["mean"].min(), genre_stats["mean"].max()
pad = (x_max - x_min) * 0.12
fig2.add_vline(
    x=overall_mean, line_width=1, line_color=P["axis"],
    annotation_text=f"Overall mean {overall_mean:.2f}", annotation_position="top",
    annotation_font=dict(color=P["muted"], size=12),
)
for name, mask, color, show_text in [
    (f"Highest {k}", genre_stats["genre"].isin(hi), P["s1"], True),
    (f"Lowest {k}", genre_stats["genre"].isin(lo), P["s2"], True),
    ("Other genres", ~genre_stats["genre"].isin(hi | lo), P["deemph"], False),
]:
    sub = genre_stats[mask]
    fig2.add_trace(
        go.Scatter(
            x=sub["mean"], y=sub["genre"], name=name, mode="markers+text" if show_text else "markers",
            marker=dict(size=13, color=color, line=dict(width=2, color=P["surface"])),
            text=[f"{m:.2f}" for m in sub["mean"]] if show_text else None,
            textposition="middle right", textfont=dict(color=P["ink2"], size=12),
            customdata=sub["n"],
            hovertemplate="<b>%{y}</b><br>Mean rating %{x:.2f}<br>%{customdata:,} ratings<extra></extra>",
        )
    )
fig2.update_layout(
    xaxis_title="Mean rating (1–5)",
    yaxis=dict(categoryorder="array", categoryarray=genre_stats["genre"].tolist()),
    showlegend=True,
)
fig2.update_xaxes(range=[x_min - pad, x_max + pad * 1.6], tickformat=".1f")
style(fig2, height=560)
st.plotly_chart(fig2, width="stretch", theme=None)

best = genre_stats.iloc[-1]
worst = genre_stats.iloc[0]
st.markdown(
    f"**Highest:** {', '.join(genre_stats.tail(k)['genre'][::-1])}. "
    f"**{best['genre']}** leads at **{best['mean']:.2f}** ({int(best['n']):,} ratings).  \n"
    f"**Lowest:** {', '.join(genre_stats.head(k)['genre'])}. "
    f"**{worst['genre']}** trails at **{worst['mean']:.2f}** ({int(worst['n']):,} ratings).  \n"
    f"The full spread across genres is only {x_max - x_min:.2f} points on a 5-point scale."
)
if len(hidden):
    st.caption(
        "Hidden by the minimum-ratings filter: "
        + ", ".join(f"{r.genre} ({r.n:,} ratings, mean {r['mean']:.2f})" for _, r in hidden.iterrows())
    )

with st.expander("Table view"):
    t = genre_stats.sort_values("mean", ascending=False).rename(
        columns={"genre": "Genre", "mean": "Mean rating", "n": "Ratings"}
    )
    t["Mean rating"] = t["Mean rating"].round(3)
    st.dataframe(t, hide_index=True, width="stretch")

st.divider()

# --------------------------------------------------------------------------- #
# Q3 - Ratings over time                                                       #
# --------------------------------------------------------------------------- #
st.header("3. Ratings over release year")
st.markdown(
    "Mean rating by the year the movie was **released** (not when it was rated; all "
    "ratings were collected in 1997–1998). The lower panel shows how many ratings back "
    "each point, because early years rest on a handful of movies."
)

c1, c2 = st.columns([1, 2])
with c1:
    granularity = st.radio("Group by", ["Year", "Decade"], horizontal=True)
with c2:
    min_year_n = st.slider(
        "Minimum ratings for a period to be plotted",
        min_value=1, max_value=500, value=20, step=1,
        help="Periods with fewer ratings are dropped from the line but still appear in the count panel.",
    )

time_col = "year" if granularity == "Year" else "decade"
with_year = df.dropna(subset=[time_col])
missing_year = len(df) - len(with_year)

time_stats = (
    with_year.groupby(time_col)["rating"].agg(mean="mean", n="count").reset_index()
    .rename(columns={time_col: "period"})
)
time_stats["period"] = time_stats["period"].astype(int)
plotted = time_stats[time_stats["n"] >= min_year_n]

fig3 = make_subplots(
    rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.06,
)
fig3.add_hline(
    y=overall_mean, line_width=1, line_color=P["axis"], row=1, col=1,
    annotation_text=f"Overall mean {overall_mean:.2f}", annotation_position="bottom right",
    annotation_font=dict(color=P["muted"], size=12),
)
fig3.add_trace(
    go.Scatter(
        x=plotted["period"], y=plotted["mean"], mode="lines+markers", name="Mean rating",
        line=dict(width=2, color=P["s1"], shape="linear"),
        marker=dict(size=8, color=P["s1"], line=dict(width=2, color=P["surface"])),
        customdata=plotted["n"],
        hovertemplate="<b>%{x}</b><br>Mean rating %{y:.2f}<br>%{customdata:,} ratings<extra></extra>",
    ),
    row=1, col=1,
)
fig3.add_trace(
    go.Bar(
        x=time_stats["period"], y=time_stats["n"], name="Ratings",
        marker=dict(color=P["s1_soft"], cornerradius=2),
        hovertemplate="<b>%{x}</b><br>%{y:,} ratings<extra></extra>",
    ),
    row=2, col=1,
)
fig3.update_layout(hovermode="x unified", showlegend=False, bargap=0.3)
fig3.update_yaxes(title_text="Mean rating", range=[1, 5], row=1, col=1, showgrid=True, gridcolor=P["grid"])
fig3.update_yaxes(title_text="Ratings", tickformat="~s", row=2, col=1, showgrid=True, gridcolor=P["grid"])
fig3.update_xaxes(title_text=f"Release {granularity.lower()}", row=2, col=1, showgrid=False)
fig3.update_xaxes(showgrid=False, row=1, col=1)
style(fig3, height=520)
fig3.update_xaxes(showgrid=False)
st.plotly_chart(fig3, width="stretch", theme=None)

# Narrative: compare pre-1980 vs 1990s means on the plotted data.
yr = time_stats.copy()
if granularity == "Decade":
    yr = with_year.groupby("year")["rating"].agg(mean="mean", n="count").reset_index().rename(columns={"year": "period"})
    yr["period"] = yr["period"].astype(int)
old = with_year[with_year["year"] < 1980]["rating"]
new = with_year[with_year["year"] >= 1990]["rating"]
peak = plotted.loc[plotted["mean"].idxmax()]
st.markdown(
    f"Movies released **before 1980** average **{old.mean():.2f}** ({len(old):,} ratings); "
    f"movies from the **1990s** average **{new.mean():.2f}** ({len(new):,} ratings). "
    f"The best-rated plotted {granularity.lower()} is **{int(peak['period'])}** at "
    f"**{peak['mean']:.2f}** ({int(peak['n']):,} ratings). Older films skew high because only "
    "the ones still remembered in the late 1990s were being watched and rated, while "
    "the 1990s catalogue includes every recent release, good or bad."
)
st.caption(
    f"{missing_year} ratings have no release year and are excluded from this chart. "
    f"{len(time_stats) - len(plotted)} period(s) fall below the minimum-ratings filter."
)

with st.expander("Table view"):
    t = time_stats.rename(columns={"period": granularity, "mean": "Mean rating", "n": "Ratings"})
    t["Mean rating"] = t["Mean rating"].round(3)
    st.dataframe(t, hide_index=True, width="stretch")

st.divider()

# --------------------------------------------------------------------------- #
# Q4 - Best movies with a floor                                                #
# --------------------------------------------------------------------------- #
st.header("4. Best movies, with a floor")
st.markdown(
    "Top 5 movies by mean rating, counting only movies with **at least 50 ratings**, "
    "then again with the floor raised to **150**. Movies are keyed by `movie_id`; a few "
    "titles appear under two ids in this dataset and are kept separate."
)

movie_stats = (
    df.groupby(["movie_id", "title"])["rating"].agg(mean="mean", n="count").reset_index()
)


def top_n(floor: int, n: int = 5) -> pd.DataFrame:
    return (
        movie_stats[movie_stats["n"] >= floor]
        .sort_values(["mean", "n"], ascending=[False, False])
        .head(n)
        .reset_index(drop=True)
    )


FLOORS = (50, 150)
tops = {f: top_n(f) for f in FLOORS}
in_both = set(tops[50]["movie_id"]) & set(tops[150]["movie_id"])
x_lo = min(t["mean"].min() for t in tops.values()) - 0.05
x_hi = max(t["mean"].max() for t in tops.values()) + 0.09


def wrap_title(title: str, width: int = 26) -> str:
    """Break a long title onto two lines for the y-axis; the hover keeps the full title."""
    if len(title) <= width:
        return title
    words, lines, cur = title.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "<br>".join(lines)


def top_chart(top: pd.DataFrame, floor: int) -> go.Figure:
    fig = go.Figure()
    top = top.assign(label=top["title"].map(wrap_title))
    order = top.sort_values("mean")["label"].tolist()
    for name, mask, color in [
        ("In both top-5 lists", top["movie_id"].isin(in_both), P["s1"]),
        ("Only at this floor", ~top["movie_id"].isin(in_both), P["s2"]),
    ]:
        sub = top[mask]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["mean"], y=sub["label"], mode="markers+text", name=name,
                marker=dict(size=14, color=color, line=dict(width=2, color=P["surface"])),
                text=[f"{m:.2f}" for m in sub["mean"]], textposition="middle right",
                textfont=dict(color=P["ink2"], size=12),
                customdata=list(zip(sub["title"], sub["n"])),
                hovertemplate="<b>%{customdata[0]}</b><br>Mean rating %{x:.2f}<br>%{customdata[1]:,} ratings<extra></extra>",
            )
        )
    fig.update_layout(
        title=dict(text=f"At least {floor} ratings · {int((movie_stats['n'] >= floor).sum()):,} movies qualify",
                   font=dict(color=P["ink2"], size=14), x=0),
        xaxis_title="Mean rating (1–5)",
        yaxis=dict(categoryorder="array", categoryarray=order),
        showlegend=True,
        legend=dict(y=1.12),
    )
    fig.update_xaxes(range=[x_lo, x_hi], tickformat=".2f")
    style(fig, height=380)
    fig.update_layout(margin=dict(t=70))
    return fig


col_a, col_b = st.columns(2)
for col, floor in zip((col_a, col_b), FLOORS):
    with col:
        st.plotly_chart(top_chart(tops[floor], floor), width="stretch", theme=None)

dropped = tops[50][~tops[50]["movie_id"].isin(in_both)]
added = tops[150][~tops[150]["movie_id"].isin(in_both)]


def fmt(rows: pd.DataFrame) -> str:
    return "; ".join(f"**{r.title}** ({r['mean']:.2f}, {int(r.n)} ratings)" for _, r in rows.iterrows())


st.markdown(
    f"**What changes when the floor rises from 50 to 150:**  \n"
    f"- Drop out (fewer than 150 ratings): {fmt(dropped) if len(dropped) else 'nothing'}.  \n"
    f"- Enter the top 5: {fmt(added) if len(added) else 'nothing'}.  \n"
    f"- Stay in both lists: {', '.join(tops[150][tops[150]['movie_id'].isin(in_both)]['title'])}.  \n"
    "Raising the floor trades small-sample favourites (cult and short films rated by a few hundred "
    "people or fewer) for widely-seen classics whose high means rest on far more votes."
)

with st.expander("Table view and custom floor"):
    floor = st.slider("Minimum ratings", min_value=1, max_value=int(movie_stats["n"].max()), value=50, step=1)
    t = top_n(floor, 10).rename(columns={"title": "Title", "mean": "Mean rating", "n": "Ratings"})
    t["Mean rating"] = t["Mean rating"].round(3)
    st.caption(f"Top 10 with at least {floor} ratings · {int((movie_stats['n'] >= floor).sum()):,} movies qualify")
    st.dataframe(t[["Title", "Mean rating", "Ratings"]], hide_index=True, width="stretch")
