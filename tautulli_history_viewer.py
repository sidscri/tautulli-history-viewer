import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# Load the Plex-visible Tautulli history
@st.cache_data
def load_data():
    df = pd.read_csv("tautulli_plex_merged_visible.csv")
    df["started_dt"] = pd.to_datetime(df["started"], unit="s", errors="coerce")
    df["stopped_dt"] = pd.to_datetime(df["stopped"], unit="s", errors="coerce")
    df["duration_minutes"] = (df["stopped_dt"] - df["started_dt"]).dt.total_seconds() / 60
    df["hour"] = df["started_dt"].dt.hour
    df["weekday"] = df["started_dt"].dt.day_name()
    return df

df = load_data()

# Sidebar filters
st.sidebar.title("Filters")
user_filter = st.sidebar.multiselect("User", sorted(df["username"].unique()), default=list(df["username"].unique()))
media_filter = st.sidebar.multiselect("Media Type", df["media_type"].unique(), default=list(df["media_type"].unique()))
date_range = st.sidebar.date_input("Date Range", [df["started_dt"].min(), df["started_dt"].max()])
duration_min = st.sidebar.slider("Minimum Duration (minutes)", 0, 300, 10)

# Apply filters
filtered = df[
    (df["username"].isin(user_filter)) &
    (df["media_type"].isin(media_filter)) &
    (df["started_dt"].dt.date >= date_range[0]) &
    (df["started_dt"].dt.date <= date_range[1]) &
    (df["duration_minutes"] >= duration_min)
].copy()

# Sort by duration
filtered.sort_values(by="duration_minutes", ascending=False, inplace=True)

# Page layout with tabs
st.title("Tautulli Plex Watch History Viewer")
tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📈 Dashboard", "📋 History Table", "📅 Monthly Summary",
    "📆 Yearly Summary", "👤 User Summary", "📺 Show Breakdown",
    "🔁 User + Show Heatmap", "🕒 Time of Day", "📆 Day of Week"
])

# Helper function to download DataFrame
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# Tab 0: Dashboard
with tab0:
    st.header("📊 Overview Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Entries", f"{len(filtered):,}")
    col2.metric("Unique Users", f"{filtered['username'].nunique():,}")
    col3.metric("Total Minutes Watched", f"{int(filtered['duration_minutes'].sum()):,}")

    top_shows = filtered["grandparent_title"].value_counts().head(5)
    st.subheader("Top 5 Shows")
    st.bar_chart(top_shows)

    top_users = filtered["username"].value_counts().head(5)
    st.subheader("Top 5 Users")
    st.bar_chart(top_users)

# Tab 1: Full history table
with tab1:
    st.write(f"Showing {len(filtered):,} of {len(df):,} total entries")
    display_df = filtered[[
        "username", "media_type", "title", "parent_title", "grandparent_title",
        "started_dt", "stopped_dt", "duration_minutes"
    ]].rename(columns={
        "username": "User",
        "media_type": "Media Type",
        "title": "Title",
        "parent_title": "Episode",
        "grandparent_title": "Show",
        "started_dt": "Start Time",
        "stopped_dt": "Stop Time",
        "duration_minutes": "Duration (min)"
    })
    st.dataframe(display_df)
    st.download_button("⬇ Download Table as CSV", convert_df_to_csv(display_df), "history_filtered.csv", "text/csv")

# Tab 2: Monthly summary
with tab2:
    monthly = filtered.copy()
    monthly["month"] = monthly["started_dt"].dt.to_period("M")
    summary = monthly.groupby("month").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    summary.index = summary.index.astype(str)
    st.bar_chart(summary["views"])
    st.line_chart(summary["minutes"])
    st.dataframe(summary.reset_index())
    st.download_button("⬇ Download Monthly Summary", convert_df_to_csv(summary.reset_index()), "monthly_summary.csv", "text/csv")

# Tab 3: Yearly summary
with tab3:
    yearly = filtered.copy()
    yearly["year"] = yearly["started_dt"].dt.year
    year_range = st.slider("Filter by Year", int(yearly["year"].min()), int(yearly["year"].max()), (int(yearly["year"].min()), int(yearly["year"].max())))
    yearly = yearly[(yearly["year"] >= year_range[0]) & (yearly["year"] <= year_range[1])]
    summary = yearly.groupby("year").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    st.bar_chart(summary["views"])
    st.line_chart(summary["minutes"])
    fig, ax = plt.subplots()
    ax.pie(summary["views"], labels=summary.index.astype(str), autopct='%1.1f%%')
    st.pyplot(fig)
    st.dataframe(summary.reset_index())
    st.download_button("⬇ Download Yearly Summary", convert_df_to_csv(summary.reset_index()), "yearly_summary.csv", "text/csv")

# Tab 4: User summary
with tab4:
    top_n = st.slider("Top N Users", 1, 50, 10)
    summary = filtered.groupby("username").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    summary = summary.sort_values(by="views", ascending=False).head(top_n)
    st.bar_chart(summary["views"])
    st.line_chart(summary["minutes"])
    fig, ax = plt.subplots()
    ax.pie(summary["views"], labels=summary.index, autopct='%1.1f%%')
    st.pyplot(fig)
    st.dataframe(summary.reset_index())
    st.download_button("⬇ Download User Summary", convert_df_to_csv(summary.reset_index()), "user_summary.csv", "text/csv")

# Tab 5: Show breakdown
with tab5:
    top_n = st.slider("Top N Shows", 1, 50, 20)
    summary = filtered.groupby("grandparent_title").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    summary = summary.sort_values(by="views", ascending=False).head(top_n)
    st.bar_chart(summary["views"])
    st.line_chart(summary["minutes"])
    st.dataframe(summary.reset_index())
    st.download_button("⬇ Download Show Breakdown", convert_df_to_csv(summary.reset_index()), "show_summary.csv", "text/csv")

    if st.checkbox("Show Pie Chart of Top Shows"):
        fig, ax = plt.subplots()
        ax.pie(summary["views"], labels=summary.index, autopct='%1.1f%%')
        st.pyplot(fig)

# Tab 6: User + Show Heatmap
with tab6:
    st.subheader("Heatmap of Views by User and Show")
    heat_df = filtered.groupby(["username", "grandparent_title"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.heatmap(heat_df, cmap="viridis", ax=ax)
    st.pyplot(fig)
    st.download_button("⬇ Download Heatmap Data", convert_df_to_csv(heat_df.reset_index()), "user_show_heatmap.csv", "text/csv")

# Tab 7: Time of Day Breakdown
with tab7:
    st.subheader("Views by Hour of Day")
    hour_summary = filtered.groupby("hour").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    st.bar_chart(hour_summary["views"])
    st.line_chart(hour_summary["minutes"])
    st.dataframe(hour_summary.reset_index())
    st.download_button("⬇ Download Hourly Breakdown", convert_df_to_csv(hour_summary.reset_index()), "hourly_summary.csv", "text/csv")

# Tab 8: Day of Week Breakdown
with tab8:
    st.subheader("Views by Day of the Week")
    weekday_summary = filtered.groupby("weekday").agg(views=("rating_key", "count"), minutes=("duration_minutes", "sum"))
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_summary = weekday_summary.reindex(weekday_order)
    st.bar_chart(weekday_summary["views"])
    st.line_chart(weekday_summary["minutes"])
    st.dataframe(weekday_summary.reset_index())
    st.download_button("⬇ Download Weekday Breakdown", convert_df_to_csv(weekday_summary.reset_index()), "weekday_summary.csv", "text/csv")
