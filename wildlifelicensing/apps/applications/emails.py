import logging

from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.encoding import smart_text

from django_hosts import reverse as hosts_reverse

from wildlifelicensing.apps.emails.emails import TemplateEmailBase
from wildlifelicensing.apps.applications.models import ApplicationLogEntry, IDRequest, ReturnsRequest, AmendmentRequest

SYSTEM_NAME = 'Wildlife Licensing Automated Message'

logger = logging.getLogger(__name__)


class ApplicationAmendmentRequestedEmail(TemplateEmailBase):
    subject = 'An amendment to your wildlife licensing application is required.'
    html_template = 'wl/emails/application_amendment_requested.html'
    txt_template = 'wl/emails/application_amendment_requested.txt'


def send_amendment_requested_email(amendment_request, request):
    application = amendment_request.application
    email = ApplicationAmendmentRequestedEmail()
    url = request.build_absolute_uri(
        reverse('wl_applications:edit_application',
                args=[application.licence_type.code_slug, application.pk])
    )

    context = {
        'amendment_request': amendment_request,
        'url': url
    }

    if amendment_request.reason:
        context['reason'] = dict(AmendmentRequest.REASON_CHOICES)[amendment_request.reason]

    if application.proxy_applicant is None:
        recipient_email = application.applicant_profile.email
    else:
        recipient_email = application.proxy_applicant.email

    msg = email.send(recipient_email, context=context)
    _log_email(msg, application=application, sender=request.user)


class ApplicationAssessmentRequestedEmail(TemplateEmailBase):
    subject = 'An assessment to a wildlife licensing application is required.'
    html_template = 'wl/emails/application_assessment_requested.html'
    txt_template = 'wl/emails/application_assessment_requested.txt'


def send_assessment_requested_email(assessment, request):
    application = assessment.application

    email = ApplicationAssessmentRequestedEmail()
    url = request.build_absolute_uri(
        reverse('wl_applications:enter_conditions_assessor',
                args=[application.pk, assessment.pk])
    )
    context = {
        'url': url
    }
    msg = email.send(assessment.assessor_group.email, context=context)

    _log_email(msg, application=application, sender=request.user)


class ApplicationAssessmentReminderEmail(TemplateEmailBase):
    subject = 'Reminder: An assessment to a wildlife licensing application is required.'
    html_template = 'wl/emails/application_assessment_reminder.html'
    txt_template = 'wl/emails/application_assessment_reminder.txt'


def send_assessment_reminder_email(assessment, request):
    application = assessment.application

    email = ApplicationAssessmentReminderEmail()
    url = request.build_absolute_uri(
        reverse('wl_applications:enter_conditions_assessor',
                args=[application.pk, assessment.pk])
    )
    context = {
        'assessor': assessment.assessor_group,
        'url': url
    }
    msg = email.send(assessment.assessor_group.email, context=context)
    _log_email(msg, application=application, sender=request.user)


class ApplicationAssessmentDoneEmail(TemplateEmailBase):
    subject = 'An assessment to a wildlife licensing application has been done.'
    html_template = 'wl/emails/application_assessment_done.html'
    txt_template = 'wl/emails/application_assessment_done.txt'


def send_assessment_done_email(assessment, request):
    application = assessment.application

    email = ApplicationAssessmentDoneEmail()
    url = request.build_absolute_uri(
        reverse('wl_applications:enter_conditions',
                args=[application.pk])
    )
    context = {
        'assessor': request.user,
        'assessor_group': assessment.assessor_group,
        'url': url
    }
    to_email = application.assigned_officer.email if application.assigned_officer else settings.WILDLIFELICENSING_EMAIL_CATCHALL
    msg = email.send(to_email, context=context)
    _log_email(msg, application=application, sender=request.user)


class ApplicationIDUpdateRequestedEmail(TemplateEmailBase):
    subject = 'An ID update for a wildlife licensing application is required.'
    html_template = 'wl/emails/application_id_request.html'
    txt_template = 'wl/emails/application_id_request.txt'


def send_id_update_request_email(id_request, request):
    application = id_request.application
    email = ApplicationIDUpdateRequestedEmail()
    url = request.build_absolute_uri(
        reverse('wl_main:identification')
    )

    if id_request.reason:
        id_request.reason = dict(IDRequest.REASON_CHOICES)[id_request.reason]

    context = {
        'id_request': id_request,
        'url': url
    }

    if application.proxy_applicant is None:
        recipient_email = application.applicant_profile.email
    else:
        recipient_email = application.proxy_applicant.email

    msg = email.send(recipient_email, context=context)
    _log_email(msg, application=application, sender=request.user)


class ApplicationReturnsRequestedEmail(TemplateEmailBase):
    subject = 'Completion of returns for a wildlife licensing application is required.'
    html_template = 'wl/emails/application_returns_request.html'
    txt_template = 'wl/emails/application_returns_request.txt'


def send_returns_request_email(returns_request, request):
    application = returns_request.application
    email = ApplicationReturnsRequestedEmail()
    url = request.build_absolute_uri(
        reverse('wl_dashboard:home')
    )

    if returns_request.reason:
        returns_request.reason = dict(ReturnsRequest.REASON_CHOICES)[returns_request.reason]

    context = {
        'url': url,
        'returns_request': returns_request
    }

    if application.proxy_applicant is None:
        recipient_email = application.applicant_profile.email
    else:
        recipient_email = application.proxy_applicant.email

    msg = email.send(recipient_email, context=context)
    _log_email(msg, application=application, sender=request.user)


class LicenceIssuedEmail(TemplateEmailBase):
    subject = 'Your wildlife licensing licence has been issued.'
    html_template = 'wl/emails/licence_issued.html'
    txt_template = 'wl/emails/licence_issued.txt'


def send_licence_issued_email(licence, application, request):
    email = LicenceIssuedEmail()
    url = request.build_absolute_uri(
        reverse('wl_dashboard:home')
    )
    context = {
        'url': url,
        'cover_letter_message': licence.cover_letter_message
    }
    if licence.licence_document is not None:
        file_name = 'WL_licence_' + smart_text(licence.licence_type.code_slug)
        if licence.licence_number:
            file_name += '_' + smart_text(licence.licence_number)
        if licence.licence_sequence:
            file_name += '-' + smart_text(licence.licence_sequence)
        elif licence.start_date:
            file_name += '_' + smart_text(licence.start_date)
        file_name += '.pdf'
        attachment = (file_name, licence.licence_document.file.read(), 'application/pdf')
        attachments = [attachment]
    else:
        logger.error('The licence pk=' + licence.pk + ' has no document associated with it.')
        attachments = None

    msg = email.send(licence.profile.email, context=context, attachments=attachments)
    log_entry = _log_email(msg, application=application, sender=request.user)
    if licence.licence_document is not None:
        log_entry.document = licence.licence_document
        log_entry.save()
    return log_entry


class LicenceRenewalNotificationEmail(TemplateEmailBase):
    subject = 'Your wildlife licence is due for renewal.'
    html_template = 'wl/emails/renew_licence_notification.html'
    txt_template = 'wl/emails/renew_licence_notification.txt'


def send_licence_renewal_email_notification(licence):
    email = LicenceRenewalNotificationEmail()
    url = 'http:' + hosts_reverse('wl_home')

    context = {
        'url': url,
        'licence': licence
    }

    email.send(licence.profile.email, context=context)


class UserNameChangeNotificationEmail(TemplateEmailBase):
    subject = 'User has changed name and requires licence reissue.'
    html_template = 'wl/emails/user_name_change_notification.html'
    txt_template = 'wl/emails/user_name_change_notification.txt'


def send_user_name_change_notification_email(licence):
    email = UserNameChangeNotificationEmail()

    url = 'http:' + hosts_reverse('wl_applications:reissue_licence', args=(licence.pk,))

    context = {
        'licence': licence,
        'url': url
    }
    email.send(licence.issuer.email, context=context)


def _log_email(email_message, application, sender=None):
    if isinstance(email_message, (EmailMultiAlternatives, EmailMessage,)):
        # TODO this will log the plain text body, should we log the html instead
        text = email_message.body
        subject = email_message.subject
        fromm = smart_text(sender) if sender else smart_text(email_message.from_email)
        # the to email is normally a list
        if isinstance(email_message.to, list):
            to = ';'.join(email_message.to)
        else:
            to = smart_text(email_message.to)
    else:
        text = smart_text(email_message)
        subject = ''
        to = application.applicant_profile.user.email
        fromm = smart_text(sender) if sender else SYSTEM_NAME

    customer = application.applicant_profile.user

    officer = sender

    kwargs = {
        'subject': subject,
        'text': text,
        'application': application,
        'customer': customer,
        'officer': officer,
        'to': to,
        'fromm': fromm
    }
    email_entry = ApplicationLogEntry.objects.create(**kwargs)
    return email_entry
