"""MODEL v4.3.0: write outputs/data/ed_number_map.csv (figure_plan.ED_NUMBER_MAP) without rerunning the model;
MODEL v4.3.1: and outputs/data/sf_number_map.csv (figure_plan.SF_NUMBER_MAP)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figure_plan as FP  # noqa: E402

if __name__ == '__main__':
    print(FP.write_ed_number_map())
    print(FP.write_sf_number_map())
