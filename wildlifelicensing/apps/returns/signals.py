from django.dispatch import Signal, receiver

from wildlifelicensing.apps.main.signals import licence_issued
from wildlifelicensing.apps.main.models import WildlifeLicence
from wildlifelicensing.apps.returns.utils import create_returns_due_dates
from wildlifelicensing.apps.returns.models import ReturnType, Return

return_submitted = Signal(providing_args=['ret'])


@receiver(licence_issued)
def licence_issued_callback(sender, **kwargs):
    if 'wildlife_licence' in kwargs:
        licence = WildlifeLicence.objects.get(pk=kwargs.get('wildlife_licence'))

        try:
            return_type = ReturnType.objects.get(licence_type=licence.licence_type)
        except ReturnType.DoesNotExist:
            return

        due_dates = create_returns_due_dates(licence.start_date, licence.end_date, licence.return_frequency)

        # if this is a reissue, need to consider existing returns for this licence
        existing_returns = Return.objects.filter(licence=licence)

        if existing_returns.count() > 0:
            # delete existing returns that haven't been edited
            existing_returns.filter(status__in=['current', 'future']).delete()

            # remove due dates before that latest edited return
            latest_edited_return = existing_returns.order_by('due_date').last()

            if latest_edited_return is not None:
                due_dates = [due_date for due_date in due_dates if due_date > latest_edited_return.due_date]

        returns = []
        for due_date in due_dates:
            returns.append(Return(licence=licence, return_type=return_type, due_date=due_date))

        if returns:
            returns[0].status = 'current'

        Return.objects.bulk_create(returns)
