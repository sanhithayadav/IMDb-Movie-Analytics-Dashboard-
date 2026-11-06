import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# IMDb MOVIE ANALYTICS DASHBOARD
# Covers all questions (Q1-Q6) in the supplied practical paper.
#
# Run:
#   pip install streamlit pandas plotly
#   streamlit run app.py
#
# Put your downloaded IMDb CSV in the same folder as this file,
# or upload it from the sidebar.
# ============================================================

st.set_page_config(
    page_title="IMDb Movie Analytics Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------- CSS ------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: Inter, sans-serif;
    }

    .stApp {
        background: linear-gradient(135deg, #111827 0%, #172033 55%, #111827 100%);
        color: #f8fafc;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827, #202b3e);
        border-right: 1px solid #334155;
    }

    [data-testid="stSidebar"] * {
        color: #f8fafc;
    }

    .hero {
        padding: 25px 18px;
        border-radius: 14px;
        text-align: center;
        color: white;
        background:
          linear-gradient(90deg, rgba(10,15,25,.92), rgba(10,15,25,.48)),
          url("https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=1600&q=85");
        background-size: cover;
        background-position: center;
        border: 1px solid #475569;
        margin-bottom: 14px;
    }

    .hero h1 {
        font-size: clamp(25px, 3vw, 40px);
        font-weight: 800;
        margin: 0;
    }

    .hero p {
        font-size: 19px;
        margin: 5px 0 0;
    }

    .kpi {
        border-radius: 13px;
        padding: 15px 16px;
        min-height: 100px;
        color: white;
        box-shadow: 0 5px 16px rgba(0,0,0,.20);
    }

    .kpi-label {
        font-size: 14px;
        font-weight: 700;
    }

    .kpi-value {
        font-size: 28px;
        font-weight: 800;
        margin-top: 5px;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 700;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #475569;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------- Helper functions --------------------
def find_column(dataframe, possible_names):
    """Find a column without depending on upper/lowercase or spaces."""
    normalized = {
        str(column).strip().lower().replace(" ", "").replace("_", ""): column
        for column in dataframe.columns
    }

    for name in possible_names:
        key = name.strip().lower().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]

    return None


def split_cell(value):
    """Split comma/semicolon/pipe separated genres or countries."""
    if pd.isna(value):
        return []

    return [
        item.strip()
        for item in re.split(r"[,;|]", str(value))
        if item.strip()
    ]


def to_number(series):
    """Convert numbers containing commas or currency symbols to numeric."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_gross(series):
    """
    Convert gross values such as:
      2900000000
      $2,900,000,000
      $2.9B
      850M
    into numeric USD values.
    """
    result = []

    for value in series:
        if pd.isna(value):
            result.append(float("nan"))
            continue

        text = str(value).strip().upper()
        text = text.replace("$", "").replace(",", "").replace(" ", "")

        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            result.append(float("nan"))
            continue

        number = float(match.group())
        if "B" in text:
            number *= 1_000_000_000
        elif "M" in text:
            number *= 1_000_000
        elif "K" in text:
            number *= 1_000

        result.append(number)

    return pd.Series(result, index=series.index, dtype="float64")


def money_text(value):
    if pd.isna(value):
        return "N/A"

    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"

    return f"${value:,.0f}"


def style_chart(figure, height=340):
    figure.update_layout(
        height=height,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.035)",
        font=dict(color="#e5e7eb"),
        margin=dict(l=12, r=12, t=55, b=12),
        title_font=dict(size=17),
        legend_title_text="",
    )
    figure.update_xaxes(gridcolor="rgba(148,163,184,.16)")
    figure.update_yaxes(gridcolor="rgba(148,163,184,.16)")
    return figure


# ---------------------- Sidebar / CSV -----------------------
st.sidebar.markdown("# 🟨 IMDb")
st.sidebar.markdown("## Movie Analytics Dashboard")
st.sidebar.divider()
st.sidebar.markdown("### Dataset Information")

uploaded_file = st.sidebar.file_uploader(
    "Upload IMDb Top 250 CSV",
    type=["csv"],
)

df = None
load_error = None

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as error:
        load_error = str(error)
else:
    possible_files = [
        Path("imdb_top_250.csv"),
        Path("IMDb Top 250 Movies.csv"),
        Path("imdb_top_250_movies.csv"),
        Path("movies.csv"),
        Path("imdb.csv"),
    ]

    for csv_path in possible_files:
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
                break
            except Exception as error:
                load_error = str(error)

st.markdown(
    """
    <div class="hero">
        <h1>IMDb Movie Analytics Dashboard</h1>
        <p>Explore. Analyze. Discover.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if df is None:
    if load_error:
        st.error(f"Unable to read the CSV file: {load_error}")

    st.warning(
        "Upload your IMDb Top 250 Movies CSV using the sidebar. "
        "The question paper provides the dataset link, but the CSV itself "
        "must be downloaded separately."
    )
    st.info(
        "After downloading the CSV, upload it here. You can also place it "
        "in the same folder as app.py and name it imdb_top_250.csv."
    )
    st.stop()

if df.empty:
    st.error("The uploaded CSV has no records.")
    st.stop()


# ---------------------- Detect columns ----------------------
title_col = find_column(
    df, ["title", "movieTitle", "name", "primaryTitle"]
)
rating_col = find_column(
    df, ["averageRating", "imdbRating", "rating", "imdb_rating"]
)
votes_col = find_column(
    df, ["numVotes", "votes", "voteCount", "numberOfVotes"]
)
genre_col = find_column(df, ["genres", "genre"])
country_col = find_column(
    df, ["countries", "country", "countryOfOrigin", "originCountry"]
)
gross_col = find_column(
    df,
    [
        "grossWorldwide",
        "worldwideGross",
        "worldwide_gross",
        "gross",
        "boxOffice",
    ],
)

if title_col is None:
    st.error(
        "Movie title column not found. Your CSV should contain a column "
        "such as title, movieTitle, or primaryTitle."
    )
    st.write("Columns found in your CSV:", list(df.columns))
    st.stop()


# ---------------------- Prepare data ------------------------
movies = df.copy()

movies["_title"] = movies[title_col].fillna("Unknown").astype(str)

if genre_col:
    movies["_genres"] = movies[genre_col].apply(split_cell)
else:
    movies["_genres"] = [[] for _ in range(len(movies))]

if country_col:
    movies["_countries"] = movies[country_col].apply(split_cell)
else:
    movies["_countries"] = [[] for _ in range(len(movies))]

if rating_col:
    movies["_rating"] = to_number(movies[rating_col])
else:
    movies["_rating"] = float("nan")

if votes_col:
    movies["_votes"] = to_number(movies[votes_col]).fillna(0)
else:
    movies["_votes"] = 0

if gross_col:
    movies["_gross"] = parse_gross(movies[gross_col])
else:
    movies["_gross"] = float("nan")


# ---------------- Sidebar dataset details -------------------
st.sidebar.metric("Rows", f"{len(df):,}")
st.sidebar.metric("Columns", f"{len(df.columns):,}")

with st.sidebar.expander("Show column names"):
    st.write(list(df.columns))


# ============================================================
# QUESTION 1: DATASET LOADING AND INITIAL EXPLORATION
# ============================================================
with st.expander("📁 Dataset Loading and Initial Exploration — Question 1"):
    st.success("Dataset loaded successfully!")

    st.subheader("First 10 records")
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    info_left, info_right = st.columns(2)

    with info_left:
        st.subheader("Dataset shape")
        st.write(f"Total rows: **{df.shape[0]}**")
        st.write(f"Total columns: **{df.shape[1]}**")

        st.subheader("Column names")
        st.write(list(df.columns))

    with info_right:
        st.subheader("Column data types")
        dtypes_df = pd.DataFrame(
            {
                "Column": df.columns,
                "Data Type": df.dtypes.astype(str).values,
            }
        )
        st.dataframe(dtypes_df, use_container_width=True, hide_index=True)

        st.subheader("Missing values in each column")
        missing_df = df.isnull().sum().reset_index()
        missing_df.columns = ["Column", "Missing Values"]
        st.dataframe(missing_df, use_container_width=True, hide_index=True)


# ============================================================
# QUESTION 2: KPI METRICS
# ============================================================
total_movies = len(movies)
average_rating = movies["_rating"].mean()
highest_rating = movies["_rating"].max()
total_votes = movies["_votes"].sum()

kpi_columns = st.columns(4)

kpi_items = [
    (
        "🎬 Total Movies",
        f"{total_movies:,}",
        "linear-gradient(135deg,#0878d1,#1764ad)",
    ),
    (
        "⭐ Average IMDb Rating",
        f"{average_rating:.1f}" if pd.notna(average_rating) else "N/A",
        "linear-gradient(135deg,#16a765,#15945a)",
    ),
    (
        "🏆 Highest Rating",
        f"{highest_rating:.1f}" if pd.notna(highest_rating) else "N/A",
        "linear-gradient(135deg,#8546d8,#6935b4)",
    ),
    (
        "👥 Total Votes",
        f"{total_votes:,.0f}",
        "linear-gradient(135deg,#ff9415,#f07800)",
    ),
]

for column, (label, value, background) in zip(kpi_columns, kpi_items):
    with column:
        st.markdown(
            f"""
            <div class="kpi" style="background:{background}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()


# ============================================================
# QUESTION 3: DATA VISUALIZATION
# QUESTION 4: TABS, EXPANDER, DIVIDER, MESSAGES
# ============================================================
genre_tab, rating_tab, gross_tab = st.tabs(
    ["📊 Genre Analysis", "🥧 Rating Analysis", "🪙 Gross Collection"]
)

# Question 3(a): genre bar chart
with genre_tab:
    st.subheader("🎞️ Movies by Genre")

    genre_data = movies["_genres"].explode().dropna()
    if not genre_data.empty:
        genre_counts = (
            genre_data.value_counts()
            .rename_axis("Genre")
            .reset_index(name="Movie Count")
            .head(15)
        )

        genre_chart = px.bar(
            genre_counts,
            x="Genre",
            y="Movie Count",
            color="Genre",
            text="Movie Count",
            title="Number of Movies by Genre",
        )
        genre_chart.update_traces(
            textposition="outside",
            showlegend=False,
        )
        st.plotly_chart(
            style_chart(genre_chart, 390),
            use_container_width=True,
        )
    else:
        st.info("Genre chart unavailable. Check the genre column in your CSV.")

# Question 3(b): rating histogram
# Question 3(c): rating versus votes scatter plot
with rating_tab:
    st.subheader("IMDb Rating Distribution")

    valid_ratings = movies["_rating"].dropna()

    if not valid_ratings.empty:
        rating_chart = px.histogram(
            x=valid_ratings,
            nbins=14,
            labels={
                "x": "IMDb Rating",
                "count": "Number of Movies",
            },
            title="Distribution of IMDb Ratings",
        )
        rating_chart.update_traces(marker_color="#3187f5")
        st.plotly_chart(
            style_chart(rating_chart, 350),
            use_container_width=True,
        )
    else:
        st.info("No numeric IMDb ratings were found.")

    st.subheader("Rating vs Number of Votes")

    scatter_data = movies.dropna(subset=["_rating"]).copy()

    if not scatter_data.empty:
        scatter_chart = px.scatter(
            scatter_data,
            x="_rating",
            y="_votes",
            hover_name="_title",
            labels={
                "_rating": "IMDb Rating",
                "_votes": "Number of Votes",
            },
            title="Relationship Between IMDb Rating and Votes",
        )
        scatter_chart.update_yaxes(type="log")
        scatter_chart.update_traces(
            marker=dict(color="#2991f5", size=8, opacity=0.72)
        )
        st.plotly_chart(
            style_chart(scatter_chart, 390),
            use_container_width=True,
        )

# Question 3(d): top 10 gross collection
with gross_tab:
    st.subheader("🏆 Top 10 Movies by Worldwide Gross")

    top_gross = (
        movies.dropna(subset=["_gross"])
        .sort_values("_gross", ascending=False)
        .head(10)
        .copy()
    )

    if not top_gross.empty:
        top_gross["_gross_label"] = top_gross["_gross"].apply(money_text)

        gross_chart = px.bar(
            top_gross.sort_values("_gross"),
            x="_gross",
            y="_title",
            orientation="h",
            text="_gross_label",
            labels={
                "_gross": "Worldwide Gross (USD)",
                "_title": "Movie Title",
            },
            title="Top 10 Movies by Worldwide Gross",
        )
        gross_chart.update_traces(
            marker_color="#ff9415",
            textposition="outside",
        )
        st.plotly_chart(
            style_chart(gross_chart, 430),
            use_container_width=True,
        )

        if gross_col:
            st.dataframe(
                top_gross[[title_col, gross_col]],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info(
            "Worldwide gross chart unavailable. Check whether your CSV "
            "contains grossWorldwide values."
        )

st.success(
    f"Dashboard loaded successfully! Explore the {total_movies:,} movies."
)


# ============================================================
# QUESTION 5: INTERACTIVE MOVIE EXPLORER
# ============================================================
st.divider()
st.header("🔎 Interactive Movie Explorer")

# Reset by changing widget keys. This safely resets all explorer widgets.
if "explorer_reset_count" not in st.session_state:
    st.session_state.explorer_reset_count = 0

if st.button("↻ Reset Explorer Filters", key="reset_explorer_button"):
    st.session_state.explorer_reset_count += 1
    st.rerun()

reset_id = st.session_state.explorer_reset_count

available_genres = sorted(
    {genre for genre_list in movies["_genres"] for genre in genre_list}
)
available_countries = sorted(
    {country for country_list in movies["_countries"] for country in country_list}
)

filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1.2])

with filter_col1:
    selected_genre = st.selectbox(
        "Genre",
        ["All"] + available_genres,
        key=f"explorer_genre_{reset_id}",
    )

with filter_col2:
    selected_countries = st.multiselect(
        "Countries",
        available_countries,
        key=f"explorer_countries_{reset_id}",
    )

with filter_col3:
    if movies["_rating"].notna().any():
        rating_min = float(movies["_rating"].min())
        rating_max = float(movies["_rating"].max())

        if rating_min == rating_max:
            rating_max = rating_min + 0.1

        rating_range = st.slider(
            "IMDb Rating Range",
            min_value=rating_min,
            max_value=rating_max,
            value=(rating_min, rating_max),
            step=0.1,
            key=f"explorer_rating_{reset_id}",
        )
    else:
        rating_range = (0.0, 10.0)
        st.info("Rating filter is unavailable because ratings were not found.")

filter_col4, filter_col5, filter_col6 = st.columns([1, 1.5, 1])

with filter_col4:
    minimum_votes = st.number_input(
        "Minimum Votes",
        min_value=0,
        value=0,
        step=1000,
        key=f"explorer_votes_{reset_id}",
    )

with filter_col5:
    title_search = st.text_input(
        "Search Movie Title",
        placeholder="Enter movie title...",
        key=f"explorer_title_{reset_id}",
    )

with filter_col6:
    sort_order = st.radio(
        "Sort IMDb Rating",
        ["Ascending", "Descending"],
        index=1,
        key=f"explorer_sort_{reset_id}",
    )

# Apply every filter to the same DataFrame copy.
filtered_movies = movies.copy()

if selected_genre != "All":
    filtered_movies = filtered_movies[
        filtered_movies["_genres"].apply(
            lambda genre_list: selected_genre in genre_list
        )
    ]

if selected_countries:
    filtered_movies = filtered_movies[
        filtered_movies["_countries"].apply(
            lambda country_list: any(
                country in country_list for country in selected_countries
            )
        )
    ]

filtered_movies = filtered_movies[
    filtered_movies["_rating"].between(
        rating_range[0], rating_range[1], inclusive="both"
    )
]

filtered_movies = filtered_movies[
    filtered_movies["_votes"] >= minimum_votes
]

if title_search.strip():
    filtered_movies = filtered_movies[
        filtered_movies["_title"].str.contains(
            title_search.strip(),
            case=False,
            na=False,
            regex=False,
        )
    ]

filtered_movies = filtered_movies.sort_values(
    "_rating",
    ascending=(sort_order == "Ascending"),
    na_position="last",
)

st.info(f"Filtered Movies: **{len(filtered_movies):,}**")

display_columns = [
    column
    for column in [title_col, genre_col, country_col, rating_col, votes_col, gross_col]
    if column is not None
]
display_columns = list(dict.fromkeys(display_columns))

if filtered_movies.empty:
    st.warning("No movies match all the selected filters.")
else:
    st.dataframe(
        filtered_movies[display_columns],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# QUESTION 6: SESSION STATE AND FORM HANDLING
# ============================================================
st.divider()
st.header("🔍 Movie Search — Form + Session State")

# Initialize session state before using it.
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

if "movie_search_message" not in st.session_state:
    st.session_state.movie_search_message = ""

# The form processes inputs only after its submit button is clicked.
with st.form("movie_search_form"):
    form_col1, form_col2, form_col3 = st.columns([1.4, 1, 1])

    with form_col1:
        form_title = st.text_input(
            "Movie Title",
            placeholder="Example: Inception",
        )

    with form_col2:
        form_genre_options = ["Any"] + available_genres
        form_genre = st.selectbox(
            "Preferred Genre",
            form_genre_options,
        )

    with form_col3:
        form_min_rating = st.slider(
            "Minimum IMDb Rating",
            min_value=0.0,
            max_value=10.0,
            value=7.0,
            step=0.1,
        )

    submitted = st.form_submit_button(
        "🔎 Search Movie",
        use_container_width=True,
    )

if submitted:
    search_results = movies.copy()

    if form_title.strip():
        search_results = search_results[
            search_results["_title"].str.contains(
                form_title.strip(),
                case=False,
                na=False,
                regex=False,
            )
        ]

    if form_genre != "Any":
        search_results = search_results[
            search_results["_genres"].apply(
                lambda genre_list: form_genre in genre_list
            )
        ]

    search_results = search_results[
        search_results["_rating"] >= form_min_rating
    ]

    if not search_results.empty:
        # Store the matching movie records in session state.
        st.session_state.selected_movie = search_results.head(10).copy()
        st.session_state.movie_search_message = (
            f"Found {len(search_results)} matching movie(s)."
        )
    else:
        st.session_state.selected_movie = None
        st.session_state.movie_search_message = (
            "No movie matched the submitted search preferences."
        )

# Display stored result after submission and on later reruns.
if st.session_state.movie_search_message:
    if st.session_state.selected_movie is not None:
        st.success(st.session_state.movie_search_message)

        result_data = st.session_state.selected_movie
        st.subheader("Matching Movie Information")

        result_columns = [
            column
            for column in [
                title_col,
                genre_col,
                rating_col,
                votes_col,
                country_col,
                gross_col,
            ]
            if column is not None
        ]
        result_columns = list(dict.fromkeys(result_columns))

        st.dataframe(
            result_data[result_columns],
            use_container_width=True,
            hide_index=True,
        )

        # Show details for the first matching movie.
        first_movie = result_data.iloc[0]
        detail1, detail2, detail3, detail4 = st.columns(4)

        with detail1:
            st.metric("Movie Title", str(first_movie["_title"]))

        with detail2:
            rating_value = first_movie["_rating"]
            st.metric(
                "IMDb Rating",
                f"{rating_value:.1f}" if pd.notna(rating_value) else "N/A",
            )

        with detail3:
            st.metric("Number of Votes", f"{first_movie['_votes']:,.0f}")

        with detail4:
            genres_text = ", ".join(first_movie["_genres"]) or "N/A"
            st.metric("Genre", genres_text)

    else:
        st.info(st.session_state.movie_search_message)


# -------------------------- Footer ---------------------------
st.divider()
st.caption(
    "IMDb Movie Analytics Dashboard | Built with Python, Streamlit, "
    "Pandas and Plotly | Practical Examination Questions 1–6"
)
