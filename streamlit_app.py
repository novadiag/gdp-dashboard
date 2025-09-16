import base64
import math
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# -----------------------------------------------------------------------------
# Declare some useful functions.

@st.cache_data
def get_gdp_data():
    """Grab GDP data from a CSV file.

    This uses caching to avoid having to read the file every time. If we were
    reading from an HTTP endpoint instead of a file, it's a good idea to set
    a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
    """

    # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
    DATA_FILENAME = Path(__file__).parent/'data/gdp_data.csv'
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    MIN_YEAR = 1960
    MAX_YEAR = 2022

    # The data above has columns like:
    # - Country Name
    # - Country Code
    # - [Stuff I don't care about]
    # - GDP for 1960
    # - GDP for 1961
    # - GDP for 1962
    # - ...
    # - GDP for 2022
    #
    # ...but I want this instead:
    # - Country Name
    # - Country Code
    # - Year
    # - GDP
    #
    # So let's pivot all those year-columns into two: Year and GDP
    gdp_df = raw_gdp_df.melt(
        ['Country Code'],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        'Year',
        'GDP',
    )

    # Convert years from string to integers
    gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

    return gdp_df


@st.cache_data
def get_schedule_html() -> str:
    """Read the static timetable HTML from disk."""

    schedule_path = Path(__file__).parent/'assets/leman_bicer_schedule.html'
    return schedule_path.read_text(encoding='utf-8')


def _build_preview_data_url(html: str) -> str:
    """Return a data URL that can be used to open the timetable in a new tab."""

    encoded = base64.b64encode(html.encode('utf-8')).decode('ascii')
    return f'data:text/html;base64,{encoded}'


def render_gdp_dashboard() -> None:
    gdp_df = get_gdp_data()

    st.markdown(
        """
        # :earth_americas: GDP dashboard

        Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
        notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
        But it's otherwise a great (and did I mention _free_?) source of data.
        """
    )

    st.write('')
    st.write('')

    min_value = gdp_df['Year'].min()
    max_value = gdp_df['Year'].max()

    from_year, to_year = st.slider(
        'Which years are you interested in?',
        min_value=min_value,
        max_value=max_value,
        value=[min_value, max_value]
    )

    countries = gdp_df['Country Code'].unique()

    if not len(countries):
        st.warning('Select at least one country')

    selected_countries = st.multiselect(
        'Which countries would you like to view?',
        countries,
        ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN']
    )

    st.write('')
    st.write('')
    st.write('')

    filtered_gdp_df = gdp_df[
        (gdp_df['Country Code'].isin(selected_countries))
        & (gdp_df['Year'] <= to_year)
        & (from_year <= gdp_df['Year'])
    ]

    st.header('GDP over time', divider='gray')

    st.write('')

    st.line_chart(
        filtered_gdp_df,
        x='Year',
        y='GDP',
        color='Country Code',
    )

    st.write('')
    st.write('')

    first_year = gdp_df[gdp_df['Year'] == from_year]
    last_year = gdp_df[gdp_df['Year'] == to_year]

    st.header(f'GDP in {to_year}', divider='gray')

    st.write('')

    cols = st.columns(4)

    for i, country in enumerate(selected_countries):
        col = cols[i % len(cols)]

        with col:
            first_gdp_series = first_year[first_year['Country Code'] == country]['GDP']
            last_gdp_series = last_year[last_year['Country Code'] == country]['GDP']

            if first_gdp_series.empty or last_gdp_series.empty:
                st.metric(
                    label=f'{country} GDP',
                    value='Data unavailable',
                    delta='n/a',
                    delta_color='off'
                )
                continue

            first_gdp = first_gdp_series.iat[0] / 1_000_000_000
            last_gdp = last_gdp_series.iat[0] / 1_000_000_000

            if math.isnan(first_gdp) or math.isnan(last_gdp):
                growth = 'n/a'
                delta_color = 'off'
            else:
                growth = f'{last_gdp / first_gdp:,.2f}x'
                delta_color = 'normal'

            st.metric(
                label=f'{country} GDP',
                value=f'{last_gdp:,.0f}B',
                delta=growth,
                delta_color=delta_color
            )


def render_schedule_view() -> None:
    st.title('LEMAN BİÇER - Ders Programı (Tablo)')
    st.caption('2025-2026 Güz Dönemi')

    schedule_html = get_schedule_html()

    preview_tab, source_tab = st.tabs(['🖼️ Ön izleme', '🧾 HTML kaynağı'])

    with preview_tab:
        st.info('Programı yazdırmadan önce aşağıdaki ön izleme (canvas) alanını kullanabilirsiniz.')

        preview_link = _build_preview_data_url(schedule_html)
        st.markdown(
            f'<a href="{preview_link}" target="_blank" rel="noopener" '
            'style="display:inline-flex;align-items:center;gap:0.5rem;padding:0.6rem 1rem;'
            'background-color:#2563eb;color:#ffffff;border-radius:0.5rem;text-decoration:none;'
            'font-weight:600;">🡥 Ön izlemeyi yeni sekmede aç</a>',
            unsafe_allow_html=True,
        )

        components.html(schedule_html, height=1100, scrolling=True)

    with source_tab:
        st.code(schedule_html, language='html')
        st.download_button(
            'HTML dosyasını indir',
            schedule_html,
            file_name='leman-bicer-ders-programi.html',
            mime='text/html',
        )


view = st.sidebar.radio(
    'Select a view',
    ('GDP dashboard', 'Leman Biçer ders programı'),
    help='Switch between the interactive GDP charts and the provided timetable.'
)

if view == 'GDP dashboard':
    render_gdp_dashboard()
else:
    render_schedule_view()
