"""
Training period rules for programs.
Easily removable module - delete this file and remove all references
in employee_summary_tab.py to disable this feature.

Business rule:
  До сентября 2026: программы B (№6-29) = 1 раз в год
  После сентября 2026: программы B (№6-29) = 1 раз в 3 года
  Программы A (№1-5): всегда 3 года
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta


TYPE_B_PROGRAMS = set(range(6, 30))


def get_training_period_years(program_id: int, b_period_3years: bool = True) -> int:
    """
    Returns training period in years for a given program.

    Args:
        program_id: Program number (1-29)
        b_period_3years: True = type B uses 3yr (post-Sept 2026),
                         False = type B uses 1yr (pre-Sept 2026)

    Returns:
        Training period in years
    """
    if program_id in TYPE_B_PROGRAMS:
        return 3 if b_period_3years else 1
    return 3


def compute_expiry_date(exam_date_str: str, program_id: int, b_period_3years: bool = True) -> datetime:
    """
    Compute the expiry date for a program given its exam date.
    """
    dt = datetime.strptime(exam_date_str.split()[0], '%d.%m.%Y')
    years = get_training_period_years(program_id, b_period_3years)
    return dt + relativedelta(years=years)


def is_program_expired(exam_date_str: str, program_id: int, b_period_3years: bool = True) -> bool:
    """
    Check if a program is expired based on exam date and training period.
    """
    try:
        expiry = compute_expiry_date(exam_date_str, program_id, b_period_3years)
        return expiry < datetime.now()
    except (ValueError, IndexError):
        return False


def get_dynamic_status(stored_status: str, exam_date: str, program_id: int, b_period_3years: bool = True) -> str:
    """
    Get effective status considering the training period setting.
    Only affects 'trained' programs on Type B when 1-year period is active.

    Args:
        stored_status: Status from DB ('trained', 'not_trained', 'expired')
        exam_date: Exam date string (DD.MM.YYYY)
        program_id: Program number
        b_period_3years: Type B period flag

    Returns:
        Effective status string
    """
    if stored_status == 'trained' and program_id in TYPE_B_PROGRAMS and not b_period_3years:
        if is_program_expired(exam_date, program_id, b_period_3years):
            return 'expired'
    return stored_status
