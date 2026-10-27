"""MODEL v4.3.0: write outputs/data/ed_number_map.csv (figure_plan.ED_NUMBER_MAP) without rerunning the model."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import figure_plan as FP  # noqa: E402

if __name__ == '__main__':
    print(FP.write_ed_number_map())
