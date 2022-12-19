import intake
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from mpl_toolkits.axes_grid1 import AxesGrid
import numpy as np
import pandas as pd
import requests
import streamlit as st
from typing import List
from typing import Dict


# ---------------------------------------------------------------------
# read actor pledge information using openClimate API
# ---------------------------------------------------------------------
@st.cache
def get_actor_pledge(actor_id: str = None) -> List[Dict]:
    server = "https://openclimate.network"
    endpoint = f"/api/v1/actor/{actor_id}"
    url = f"{server}{endpoint}"
    headers = {'Accept': 'application/json'}
    response = requests.get(url, headers=headers)
    data_list = response.json()['data']
    return data_list['targets']


def get_target_emissions(data: pd.DataFrame = None, actor_id: str = None) -> Dict:
    pledges = get_actor_pledge(actor_id)
    baseline_year = pledges[0]['baseline_year']
    target_value = float(pledges[0]['target_value'])
    baseline_emissions = data.loc[data['year']
                                  == baseline_year, 'total_emissions']
    target_emissions = baseline_emissions*((100-target_value)/100)
    return target_emissions


def get_target_emissions_dict(data: pd.DataFrame = None, actor_id: str = None) -> Dict:
    pledges = get_actor_pledge(actor_id)
    baseline_year = float(pledges[0]['baseline_year'])
    target_value = float(pledges[0]['target_value'])
    baseline_emissions = data.loc[data['year']
                                  == baseline_year, 'total_emissions']
    target_emissions = baseline_emissions*((100-target_value)/100)
    return {'target_emissions': target_emissions, 'baseline_year': baseline_year}


# ---------------------------------------------------------------------
# read actor emissions using intake-OpenClimate
# ---------------------------------------------------------------------
@st.cache
def open_catalog() -> intake.catalog.local.YAMLFileCatalog:
    catalog = "https://raw.githubusercontent.com/Open-Earth-Foundation/intake-OpenClimate/main/master.yaml"
    cat = intake.open_catalog(catalog)
    return cat


@st.cache
def read_unfccc() -> pd.DataFrame:
    cat = open_catalog()
    return cat.emissions.unfccc.read()


def read_primap() -> pd.DataFrame:
    cat = open_catalog()
    return cat.emissions.primap.read()


@st.cache
def read_epa() -> pd.DataFrame:
    cat = open_catalog()
    return cat.emissions.epa_inventory.read()


@st.cache
def read_eccc() -> pd.DataFrame:
    cat = open_catalog()
    return cat.emissions.eccc_inventory.read()


# ---------------------------------------------------------------------
# read actor actor names using intake-OpenClimate
# ---------------------------------------------------------------------
@st.cache
def read_countries() -> pd.DataFrame:
    cat = open_catalog()
    return cat.actors.country.read()


@st.cache
def read_subnational() -> pd.DataFrame:
    cat = open_catalog()
    return cat.actors.subnational.read()


@st.cache
def get_country_names() -> List[str]:
    cat = open_catalog()
    return list(cat.actors.country.read()['name'])


# ---------------------------------------------------------------------
# layout and containers
# ---------------------------------------------------------------------
sidebar = st.sidebar
country_container = st.container()
subnational_container = st.container()

with sidebar:
    st.title("OpenClimate Data Viewer")

    st.markdown('''
    A [streamlit](https://streamlit.io/) app
    to visualize reported emissions data.
    ''')

    st.markdown("---")
    st.subheader(
        "Code available on [GitHub](https://github.com/)")

with country_container:
    # load data, it is cached for speed
    country_names = get_country_names()
    countries = read_countries()
    unfccc = read_unfccc()

    st.title("Time series of country emissions")
    st.markdown('''
    Here you can display country emissions for Annex 1 countries. Data is from [UNFCCC](https://di.unfccc.int/time_series).
    ''')

    with st.expander("Click here to start plotting emissions!"):
        # select countires
        options = st.multiselect(
            'Which countries do you want to display?',
            country_names,
            default=['Canada'])

        # list of selected country codes
        country_codes = countries.loc[countries['name'].isin(options), 'actor']

        st.subheader("Country Emissions")
        # create figure
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111)

        ymax = 0.1
        for actor_id in country_codes:
            # tonnes to giggatonnes
            conversion = 1 / 10**9

            # get data for actor_id
            data = unfccc.loc[unfccc['actor'] == actor_id]

            # set the max value, this is kludgy
            ymax_tmp = (data['total_emissions'] * conversion).max()
            ymax = ymax_tmp if ymax_tmp > ymax else ymax

            # target emissions
            #target_emissions = get_target_emissions(data, actor_id) * conversion
            target_dict = get_target_emissions_dict(data, actor_id)
            target_emissions = target_dict['target_emissions'] * conversion
            baseline_year = target_dict['baseline_year']

            # plot for aeach actor
            ax.plot(data['year'],
                    data['total_emissions'] * conversion, linewidth=2, label=actor_id)

            # get pledges
            ax.plot([baseline_year, list(data['year'])[-1]],
                    [target_emissions, target_emissions], '--', label=f'{actor_id} target level')

            ax.set_ylim([0, ymax])
            ax.set_xlim([1990, 2022])

            # Turn off the display of all ticks.
            ax.tick_params(which='both',  # Options for both major and minor ticks
                           top='off',        # turn off top ticks
                           left='off',       # turn off left ticks
                           right='off',      # turn off right ticks
                           bottom='off')     # turn off bottom ticks

            # Remove x tick marks
            plt.setp(ax.get_xticklabels(), rotation=0)

            # Hide the right and top spines
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_visible(False)

            # Only show ticks on the left and bottom spines
            ax.yaxis.set_ticks_position('left')
            ax.xaxis.set_ticks_position('bottom')

            # major/minor tick lines
            # ax.minorticks_on()
            ax.yaxis.set_minor_locator(AutoMinorLocator(4))
            ax.xaxis.set_minor_locator(AutoMinorLocator(4))
            ax.grid(axis='y', which='major', color=[
                    0.8, 0.8, 0.8], linestyle='-')

            ax.set_ylabel("Emissions (GtCO$_2$e)")

        plt.legend(loc='lower right', frameon=False)

        st.pyplot(fig)


with subnational_container:
    # load data, it is cached for speed
    country_names = get_country_names()
    countries = read_countries()
    unfccc = read_unfccc()
    df_epa = read_epa()
    df_eccc = read_eccc()

    st.title("Do subnational emissions budet?")
    st.markdown('''
    Here you can explore if emissions reported from subnational actors adds up to data reported by national actors. 
    Data sources: [UNFCCC](https://di.unfccc.int/time_series), [EPA](https://cfpub.epa.gov/ghgdata/inventoryexplorer/#), and [ECCC](https://data.ec.gc.ca/data/substances/monitor/canada-s-official-greenhouse-gas-inventory/A-IPCC-Sector/?lang=en)
    ''')
    with st.expander("Click here to start exploring!"):

        # select countires
        option = st.selectbox(
            'Please select a country',
            ('Canada', 'United States of America'))

        # list of selected country codes
        actor_id = countries.loc[countries['name']
                                 == option, 'actor'].values[0]

        # ---------------------------------------------------------------------
        # Plot country and subnational total
        # ---------------------------------------------------------------------
        st.subheader("National and sum of subational emissions")
        # create figure
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111)

        # tonnes to giggatonnes
        conversion = 1 / 10**9

        # get data for actor_id
        data = unfccc.loc[unfccc['actor'] == actor_id]
        country_total = data['total_emissions'] * conversion

        # set the max value, this is kludgy
        ymax = (country_total).max()

        # plot for aeach actor
        ax.plot(data['year'], country_total, linewidth=2, label=actor_id)

        if actor_id == 'CA':
            df_sum = df_eccc[['year', 'total_emissions']
                             ].groupby(by=['year']).sum().reset_index()
            subnational_total = df_sum.total_emissions * conversion
            ax.plot(df_sum.year, subnational_total, linewidth=2,
                    label='Sum of Subnationals', linestyle='dashed')

        if actor_id == 'US':
            df_sum = df_epa[['year', 'total_emissions']
                            ].groupby(by=['year']).sum().reset_index()
            subnational_total = df_sum.total_emissions * conversion
            ax.plot(df_sum.year, subnational_total, linewidth=2,
                    label='Sum of Subnationals', linestyle='dashed')

        ax.set_ylim([0, ymax])
        ax.set_xlim([1990, 2022])

        # Turn off the display of all ticks.
        ax.tick_params(which='both',  # Options for both major and minor ticks
                       top='off',        # turn off top ticks
                       left='off',       # turn off left ticks
                       right='off',      # turn off right ticks
                       bottom='off')     # turn off bottom ticks

        # Remove x tick marks
        plt.setp(ax.get_xticklabels(), rotation=0)

        # Hide the right and top spines
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        # Only show ticks on the left and bottom spines
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

        # major/minor tick lines
        # ax.minorticks_on()
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.grid(axis='y', which='major', color=[
                0.8, 0.8, 0.8], linestyle='-')

        ax.set_ylabel("Emissions (GtCO$_2$e)")

        plt.legend(loc='lower right', frameon=False)

        st.pyplot(fig)

        # ---------------------------------------------------------------------
        # Plot difference
        # ---------------------------------------------------------------------
        st.subheader("Subnational Emissions + Difference")
        # create figure
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111)

        difference = country_total.values - subnational_total.values
        # set the max value, this is kludgy
        ymax = abs(difference).max()
        year_range = [1990, 2022]

        # reference lint
        ax.plot(year_range, [0, 0], linewidth=1, color='k')

        # plot all the subnationals
        if actor_id == 'CA':
            ind = 1
            for actor in set(df_eccc.actor):
                subnat_data = df_eccc.loc[df_eccc.actor == actor]
                subnat_emissions = subnat_data.total_emissions * conversion
                ymax_tmp = subnat_emissions.max()
                ymax = ymax_tmp if ymax_tmp > ymax else ymax
                if ind == 1:
                    ind += 1
                    ax.plot(subnat_data.year,
                            subnat_emissions, color=[0.8, 0.8, 0.8], linewidth=1, label='Subnational')
                else:
                    ax.plot(subnat_data.year,
                            subnat_emissions, color=[0.8, 0.8, 0.8], linewidth=1)

        if actor_id == 'US':
            ind = 1
            for actor in set(df_epa.actor):
                subnat_data = df_epa.loc[df_epa.actor == actor]
                subnat_emissions = subnat_data.total_emissions * conversion
                ymax_tmp = subnat_emissions.max()
                ymax = ymax_tmp if ymax_tmp > ymax else ymax
                if ind == 1:
                    ind += 1
                    ax.plot(subnat_data.year,
                            subnat_emissions, color=[0.8, 0.8, 0.8], linewidth=1, label='Subnational')
                else:
                    ax.plot(subnat_data.year,
                            subnat_emissions, color=[0.8, 0.8, 0.8], linewidth=1)

        # plot difference
        ax.plot(data['year'], difference, linewidth=2,
                label='Difference')

        ax.set_ylim([-ymax, ymax])
        ax.set_xlim(year_range)

        # Turn off the display of all ticks.
        ax.tick_params(which='both',  # Options for both major and minor ticks
                       top='off',        # turn off top ticks
                       left='off',       # turn off left ticks
                       right='off',      # turn off right ticks
                       bottom='off')     # turn off bottom ticks

        # Remove x tick marks
        plt.setp(ax.get_xticklabels(), rotation=0)

        # Hide the right and top spines
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        # Only show ticks on the left and bottom spines
        ax.yaxis.set_ticks_position('left')
        ax.xaxis.set_ticks_position('bottom')

        # major/minor tick lines
        # ax.minorticks_on()
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.xaxis.set_minor_locator(AutoMinorLocator(4))
        ax.grid(axis='y', which='major', color=[
                0.8, 0.8, 0.8], linestyle='-')

        ax.set_ylabel("Emissions (GtCO$_2$e)")

        plt.legend(loc='lower right', frameon=False)

        st.pyplot(fig)
