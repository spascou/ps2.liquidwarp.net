def dark_theme():

    lightColor: str = "#fff"
    medColor: str = "#888"

    return {
        "config": {
            "background": "#343c3d",
            "title": {"color": lightColor},
            "style": {
                "guide-label": {"fill": lightColor},
                "guide-title": {"fill": lightColor},
            },
            "axis": {
                "domainColor": lightColor,
                "gridColor": medColor,
                "tickColor": lightColor,
            },
        }
    }
