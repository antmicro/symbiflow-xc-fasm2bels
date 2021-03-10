import re
import json
import os
from .verilog_modeling import Bel, Site, make_inverter_path


def get_pcie_site(db, grid, tile, site):
    """ Return the prjxray.tile.Site object for the given PCIE site. """
    gridinfo = grid.gridinfo_at_tilename(tile)
    tile_type = db.get_tile_type(gridinfo.tile_type)

    sites = list(tile_type.get_instance_sites(gridinfo))

    for site in sites:
        if "PCIE_2_1" in site:
            return site

    assert False, (tile, site)


def process_pcie(conn, top, tile_name, features):
    """
    Processes the PCIE_BOT tile
    """

    # Filter only PCIE_2_1 related features
    pcie_features = [f for f in features if 'PCIE.' in f.feature]
    if len(pcie_features) == 0:
        return

    site = get_pcie_site(top.db, top.grid, tile=tile_name, site='PCIE_2_1')

    # Create the site
    pcie_site = Site(pcie_features, site)

    # Create the PCIE_2_1 bel and add its ports
    pcie = Bel('PCIE_2_1')
    pcie.set_bel('PCIE_2_1')

    db_root = top.db.db_root

    attrs_file = os.path.join(db_root, "cells_data", "pcie_2_1_attrs.json")
    ports_file = os.path.join(db_root, "cells_data", "pcie_2_1_ports.json")

    assert os.path.exists(attrs_file) and os.path.exists(ports_file)

    with open(attrs_file, "r") as params_file:
        params = json.load(params_file)

    with open(ports_file, "r") as ports_file:
        ports = json.load(ports_file)

    for param, param_info in params.items():
        param_type = param_info["type"]
        param_digits = param_info["digits"]

        value = None
        if param_type == "BIN":
            value = pcie_site.decode_multi_bit_feature(feature=param)
            value = "{digits}'b{value:0{digits}b}".format(
                digits=param_digits, value=value)
        elif param_type == "BOOL":
            value = '"TRUE"' if pcie_site.has_feature(param) else '"FALSE"'

        pcie.parameters[param] = value

    for port, port_data in ports.items():
        width = int(port_data["width"])
        direction = port_data["direction"]

        for i in range(width):
            if width > 1:
                port_name = "{}[{}]".format(port, i)
                wire_name = "{}{}".format(port, i)
            else:
                port_name = port
                wire_name = port

            if direction == "input":
                pcie_site.add_sink(pcie, port_name, wire_name, pcie.bel,
                                   wire_name)
            else:
                assert direction == "output", direction
                pcie_site.add_source(pcie, port_name, wire_name, pcie.bel,
                                     wire_name)

    # Add the bel
    pcie_site.add_bel(pcie)

    # Add the sites
    top.add_site(pcie_site)
