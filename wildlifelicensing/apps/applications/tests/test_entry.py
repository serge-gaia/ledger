import os

from django.core.urlresolvers import reverse
from django.core.files import File
from django.test import TestCase, TransactionTestCase

from ledger.accounts.models import EmailUser, Document, Address, Profile

from wildlifelicensing.apps.main.models import WildlifeLicenceType
from wildlifelicensing.apps.main.tests.helpers import SocialClient, get_or_create_default_customer, create_random_customer, \
    is_login_page
from wildlifelicensing.apps.applications.tests import helpers

TEST_ID_PATH = os.path.join('wildlifelicensing', 'apps', 'main', 'test_data', 'test_id.jpg')


class ApplicationEntryTestCase(TestCase):
    fixtures = ['licences.json']

    def setUp(self):
        self.customer = get_or_create_default_customer()

        self.client = SocialClient()

        licence_type = WildlifeLicenceType.objects.get(code_slug='regulation-17')
        licence_type.identification_required = True
        licence_type.save()

    def tearDown(self):
        self.client.logout()
        # clean id file
        if self.customer.identification:
            os.remove(self.customer.identification.path)

    def test_new_application(self):
        """Testing that a user begin the process of creating an application"""
        self.client.login(self.customer.email)

        # check that client can access the licence type selection list
        response = self.client.get(reverse('wl_applications:new_application'))

        self.assertRedirects(response, reverse('wl_applications:select_licence_type'),
                             status_code=302, target_status_code=200, fetch_redirect_response=False)

        # check the customer pk has been set in the session
        self.assertTrue('customer_pk' in self.client.session['application'])

        self.assertEqual(self.client.session['application']['customer_pk'], self.customer.pk)

    def test_select_licence_type(self):
        """Testing that a user can display the licence type selection list"""
        self.client.login(self.customer.email)

        # check that client can access the licence type selection list
        response = self.client.get(reverse('wl_applications:select_licence_type'))
        self.assertEqual(200, response.status_code)

    def test_check_identification_required_no_current_id(self):
        """Testing that a user can display the identification required page in the case the user has no
        current identification, and upload an ID.
        """
        self.client.login(self.customer.email)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
        }
        session.save()

        # check that client can access the identification required page
        response = self.client.get(reverse('wl_applications:check_identification', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        with open(TEST_ID_PATH, 'rb') as fp:
            post_params = {
                'identification_file': fp
            }
            response = self.client.post(reverse('wl_applications:check_identification', args=('regulation-17',)),
                                        post_params)

            self.assertRedirects(response, reverse('wl_applications:create_select_profile', args=('regulation-17',)),
                                 status_code=302, target_status_code=200, fetch_redirect_response=False)

            # update customer
            self.customer = EmailUser.objects.get(email=self.customer.email)

    def test_check_identification_required_current_id(self):
        """Testing that a user can display the identification required page in the case the user has a
        current identification.
        """
        self.client.login(self.customer.email)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
        }
        session.save()

        with open(TEST_ID_PATH, 'rb') as fp:
            self.customer.identification = Document.objects.create(name='test_id')
            self.customer.identification.file.save('test_id.jpg', File(fp), save=True)
            self.customer.save()

        # check that client is redirected to profile creation / selection page
        response = self.client.get(reverse('wl_applications:check_identification', args=('regulation-17',)))
        self.assertRedirects(response, reverse('wl_applications:create_select_profile', args=('regulation-17',)),
                             status_code=302, target_status_code=200, fetch_redirect_response=False)

    def test_create_select_profile_create(self):
        """Testing that a user can display the create / select profile page and create a profile
        in the case the user has no profile
        """
        self.client.login(self.customer.email)

        original_profile_count = self.customer.profile_set.count()

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
        }
        session.save()

        # check that client can access the profile create/select page
        response = self.client.get(reverse('wl_applications:create_select_profile', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        # check there is not a profile selection form, meaning there is no profile
        self.assertFalse('profile_selection_form' in response.context)

        post_params = {
            'user': self.customer.pk,
            'name': 'Test Profile',
            'email': 'test@testplace.net.au',
            'institution': 'Test Institution',
            'line1': '1 Test Street',
            'locality': 'Test Suburb',
            'state': 'WA',
            'country': 'AU',
            'postcode': '0001',
            'create': True
        }

        response = self.client.post(reverse('wl_applications:create_select_profile', args=('regulation-17',)), post_params)

        # check that client is redirected to enter details page
        self.assertRedirects(response, reverse('wl_applications:enter_details', args=('regulation-17',)),
                             status_code=302, target_status_code=200, fetch_redirect_response=False)

        # chech that a new profile was created
        self.assertEqual(self.customer.profile_set.count(), original_profile_count + 1)

        # check the created profile has been set in the session
        self.assertTrue('profile_pk' in self.client.session['application'])

    def test_create_select_profile_select(self):
        """Testing that a user can display the create / select profile page and select a profile
        in the case the user has one or more existing profiles
        """
        self.client.login(self.customer.email)

        # create profiles
        address1 = Address.objects.create(line1='1 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile1 = Profile.objects.create(user=self.customer, name='Test Profile', email='test@testplace.net.au',
                                          institution='Test Institution', postal_address=address1)

        address2 = Address.objects.create(line1='2 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile2 = Profile.objects.create(user=self.customer, name='Test Profile 2', email='test@testplace.net.au',
                                          institution='Test Institution', postal_address=address2)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
            'profile_pk': profile1.pk
        }
        session.save()

        # check that client can access the profile create/select page
        response = self.client.get(reverse('wl_applications:create_select_profile', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        # check there is a profile selection form, meaning there at least one existing profile
        self.assertTrue('profile_selection_form' in response.context)

        post_params = {
            'profile': profile2.pk,
            'select': True
        }

        response = self.client.post(reverse('wl_applications:create_select_profile', args=('regulation-17',)), post_params)

        # check that client is redirected to enter details page
        self.assertRedirects(response, reverse('wl_applications:enter_details', args=('regulation-17',)),
                             status_code=302, target_status_code=200, fetch_redirect_response=False)

        # check the profile has been set in the session
        self.assertTrue('profile_pk' in self.client.session['application'])

        # check that the profile in the session is the selected profile
        self.assertEqual(self.client.session['application']['profile_pk'], profile2.pk)

    def test_enter_details_draft(self):
        """Testing that a user can enter the details of an application form and save as a draft
        """
        self.client.login(self.customer.email)

        # create profiles
        address = Address.objects.create(line1='1 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile = Profile.objects.create(user=self.customer, name='Test Profile', email='test@testplace.net.au',
                                         institution='Test Institution', postal_address=address)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
            'profile_pk': profile.pk
        }
        session.save()

        original_applications_count = profile.application_set.count()

        # check that client can access the enter details page
        response = self.client.get(reverse('wl_applications:enter_details', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        post_params = {
            'project_title': 'Test Title',
            'draft': True
        }

        response = self.client.post(reverse('wl_applications:enter_details', args=('regulation-17',)), post_params)

        # check that client is redirected to the dashboard
        self.assertRedirects(response, reverse('wl_dashboard:home'), status_code=302, target_status_code=200,
                             fetch_redirect_response=False)

        # check that a new application was created
        self.assertEqual(profile.application_set.count(), original_applications_count + 1)

        # check that the state of the application is draft
        self.assertEqual(profile.application_set.first().processing_status, 'draft')

    def test_enter_details_draft_continue(self):
        """Testing that a user can enter the details of an application form and save as a draft
        and continue editing"""
        self.client.login(self.customer.email)

        # create profiles
        address = Address.objects.create(line1='1 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile = Profile.objects.create(user=self.customer, name='Test Profile', email='test@testplace.net.au',
                                         institution='Test Institution', postal_address=address)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
            'profile_pk': profile.pk
        }
        session.save()

        original_applications_count = profile.application_set.count()

        # check that client can access the enter details page
        response = self.client.get(reverse('wl_applications:enter_details', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        post_params = {
            'project_title': 'Test Title',
            'draft_continue': True
        }

        response = self.client.post(reverse('wl_applications:enter_details', args=('regulation-17',)), post_params)

        # check that client is redirected to enter details page
        self.assertRedirects(response, reverse('wl_applications:enter_details',
                                               args=('regulation-17', profile.application_set.first().pk)),
                             status_code=302, target_status_code=200, fetch_redirect_response=False)

        # check that a new application was created
        self.assertEqual(profile.application_set.count(), original_applications_count + 1)

        # check that the state of the application is draft
        self.assertEqual(profile.application_set.first().processing_status, 'draft')

    def test_enter_details_preview(self):
        """Testing that a user can enter the details of an application form and that the data is
        saved in the session for previewing
        """
        self.client.login(self.customer.email)

        # create profiles
        address = Address.objects.create(line1='1 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile = Profile.objects.create(user=self.customer, name='Test Profile', email='test@testplace.net.au',
                                         institution='Test Institution', postal_address=address)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
            'profile_pk': profile.pk
        }
        session.save()

        # check that client can access the enter details page
        response = self.client.get(reverse('wl_applications:enter_details', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        post_params = {
            'project_title-0-0': 'Test Title',
            'lodge': True
        }

        response = self.client.post(reverse('wl_applications:enter_details', args=('regulation-17',)), post_params)

        # check the data has been set in the session
        self.assertTrue('data' in self.client.session['application'])

        # check that the profile in the session is the selected profile
        self.assertEqual(self.client.session['application']['data'][0].get('project_details')[0].get('project_title'), 'Test Title')

    def test_enter_details_lodge(self):
        """Testing that a user can preview the details of an application form then lodge the application
        """
        self.client.login(self.customer.email)

        # create profiles
        address = Address.objects.create(line1='1 Test Street', locality='Test Suburb', state='WA', postcode='0001')
        profile = Profile.objects.create(user=self.customer, name='Test Profile', email='test@testplace.net.au',
                                         institution='Test Institution', postal_address=address)

        # create the application dict in the session first
        # the session must be stored in a variable in order to be modifyable
        # https://docs.djangoproject.com/en/1.9/topics/testing/tools/#persistent-state
        session = self.client.session
        session['application'] = {
            'customer_pk': self.customer.pk,
            'profile_pk': profile.pk,
            'data': {
                'project_title': 'Test Title'
            }
        }
        session.save()

        original_applications_count = profile.application_set.count()

        # check that client can access the enter details page
        response = self.client.get(reverse('wl_applications:enter_details', args=('regulation-17',)))
        self.assertEqual(200, response.status_code)

        post_params = {
            'lodge': True
        }

        response = self.client.post(reverse('wl_applications:preview', args=('regulation-17',)), post_params)

        # chech that a new applicaiton was created
        self.assertEqual(profile.application_set.count(), original_applications_count + 1)

        # check that the state of the application is draft
        self.assertEqual(profile.application_set.first().processing_status, 'new')


class ApplicationEntrySecurity(TransactionTestCase):
    def setUp(self):
        self.client = SocialClient()

    def test_user_access_other_user(self):
        """
        Test that a user cannot edit/view another user application
        """
        customer1 = create_random_customer()
        customer2 = create_random_customer()
        self.assertNotEqual(customer1, customer2)
        application1 = helpers.create_application(user=customer1)
        application2 = helpers.create_application(user=customer2)
        self.assertNotEqual(application1, application2)

        # login as user1
        self.client.login(customer1.email)
        my_url = reverse('wl_applications:enter_details_existing_application',
                         args=[application1.licence_type.code_slug, application1.pk])
        response = self.client.get(my_url)
        self.assertEqual(200, response.status_code)

        forbidden_urls = [
            reverse('wl_applications:edit_application', args=[application2.licence_type.code_slug, application2.pk]),
            reverse('wl_applications:enter_details_existing_application',
                    args=[application2.licence_type.code_slug, application2.pk]),
            reverse('wl_applications:preview', args=[application2.licence_type.code_slug, application2.pk])
        ]

        for forbidden_url in forbidden_urls:
            response = self.client.get(forbidden_url, follow=True)
            self.assertEqual(403, response.status_code)

    def test_user_access_lodged(self):
        """
        Once the application if lodged the user should not be able to edit it
        """
        customer1 = create_random_customer()

        # login as user1
        self.client.login(customer1.email)

        application = helpers.create_application(user=customer1)

        self.assertEqual('draft', application.customer_status)
        my_urls = [
            reverse('wl_applications:edit_application', args=[application.licence_type.code_slug, application.pk]),
            reverse('wl_applications:enter_details_existing_application',
                    args=[application.licence_type.code_slug, application.pk]),
            reverse('wl_applications:preview', args=[application.licence_type.code_slug, application.pk])
        ]
        for url in my_urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(200, response.status_code,
                             msg="Wrong status code {1} for {0}".format(url, response.status_code))

        # lodge the application
        url = reverse('wl_applications:preview', args=[application.licence_type.code_slug, application.pk])
        session = self.client.session
        session['application'] = {
            'customer_pk': customer1.pk,
            'profile_pk': application.applicant_profile.pk,
            'data': {
                'project_title': 'Test'
            }
        }
        session.save()
        self.client.post(url)
        application.refresh_from_db()
        self.assertEqual('under_review', application.customer_status)
        for url in my_urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(403, response.status_code)

    def test_user_not_logged_is_redirected_to_login(self):
        """
        A user not logged in should be redirected to the login page and not see a 403
        """
        customer1 = create_random_customer()
        application = helpers.create_application(user=customer1)
        self.assertEqual('draft', application.customer_status)
        my_urls = [
            reverse('wl_applications:edit_application', args=[application.licence_type.code_slug, application.pk]),
            reverse('wl_applications:enter_details_existing_application',
                    args=[application.licence_type.code_slug, application.pk]),
            reverse('wl_applications:preview', args=[application.licence_type.code_slug, application.pk])
        ]
        for url in my_urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(200, response.status_code,
                             msg="Wrong status code {1} for {0}".format(url, response.status_code))
            self.assertTrue(is_login_page(response))

        # lodge the application
        self.client.login(customer1.email)
        url = reverse('wl_applications:preview', args=[application.licence_type.code_slug, application.pk])
        session = self.client.session
        session['application'] = {
            'customer_pk': customer1.pk,
            'profile_pk': application.applicant_profile.pk,
            'data': {
                'project_title': 'Test'
            }
        }
        session.save()
        self.client.post(url)
        application.refresh_from_db()
        self.assertEqual('under_review', application.customer_status)
        # logout
        self.client.logout()
        for url in my_urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(200, response.status_code)
            self.assertTrue(is_login_page(response))
