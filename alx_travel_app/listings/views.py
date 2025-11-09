import requests
from rest_framework.decorators import api_view
from django.shortcuts import render
from rest_framework import status
from django.conf import settings
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from .models import Listing, Booking
from .serializers import ListingSerializer, BookingSerializer
from .models import Payment

CHAPA_API_URL = "https://api.chapa.co/v1/transaction/initialize"

@api_view(['POST'])
def chapa_callback(request):
    """
    Handles Chapa webhook for payment completion.
    Updates Payment model and sends confirmation email.
    """
    data = request.data
    tx_ref = data.get('tx_ref')
    payment_status = data.get('status')

    if not tx_ref or not payment_status:
        return Response({"error": "Missing tx_ref or status"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payment = Payment.objects.get(transaction_id=tx_ref)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

    if payment_status == "success":
        payment.status = "COMPLETED"
        payment.save()

        # Send email asynchronously via Celery
        send_payment_confirmation_email.delay(
            user_email=payment.booking.user_email,  # assuming Booking model has user_email
            booking_reference=payment.booking_reference,
            amount=payment.amount
        )

    else:
        payment.status = "FAILED"
        payment.save()

    return Response({"message": "Payment status updated", "status": payment.status}, status=status.HTTP_200_OK)

@api_view(['POST'])
def initiate_payment(request):
    """
    Initiates a payment with Chapa and stores the transaction with status 'Pending'.
    Expects booking_reference and amount in the request data.
    """
    booking_reference = request.data.get('booking_reference')
    amount = request.data.get('amount')

    if not booking_reference or not amount:
        return Response({"error": "booking_reference and amount are required."},
                        status=status.HTTP_400_BAD_REQUEST)

    # Data to send to Chapa
    payload = {
        "amount": amount,
        "currency": "ETB",  # Change if using another currency
        "email": "customer@example.com",  # Ideally from the booking/user
        "first_name": "John",
        "last_name": "Doe",
        "tx_ref": booking_reference,
        "callback_url": "https://yourdomain.com/payment/callback/"
    }

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(CHAPA_API_URL, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "success":
            transaction_id = data['data']['tx_ref']

            # Save to Payment model with status Pending
            Payment.objects.create(
                booking_reference=booking_reference,
                transaction_id=transaction_id,
                amount=amount,
                status="PENDING"
            )

            return Response({
                "message": "Payment initiated successfully",
                "transaction_id": transaction_id,
                "checkout_url": data['data']['checkout_url']
            }, status=status.HTTP_201_CREATED)

        return Response({"error": "Failed to initiate payment", "details": data},
                        status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Create your views here.
def home(request):
    return HttpResponse("<h1>Hello World!</h1>")

class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify"

@api_view(['GET'])
def verify_payment(request, tx_ref):
    """
    Verifies a payment with Chapa using the transaction reference.
    Updates Payment status accordingly.
    """
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(f"{CHAPA_VERIFY_URL}/{tx_ref}", headers=headers)
        data = response.json()

        # Find Payment record
        try:
            payment = Payment.objects.get(transaction_id=tx_ref)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if response.status_code == 200 and data.get("status") == "success":
            payment.status = "COMPLETED"
            payment.save()
            return Response({
                "message": "Payment verified successfully",
                "status": payment.status,
                "details": data
            }, status=status.HTTP_200_OK)
        else:
            payment.status = "FAILED"
            payment.save()
            return Response({
                "message": "Payment verification failed",
                "status": payment.status,
                "details": data
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def create_booking_and_payment(request):
    """
    1. Create a booking
    2. Initiate payment with Chapa
    3. Return checkout URL for user
    """
    user_email = request.data.get('email')
    booking_details = request.data.get('booking_details')
    amount = request.data.get('amount')

    if not user_email or not booking_details or not amount:
        return Response({"error": "email, booking_details, and amount are required."},
                        status=status.HTTP_400_BAD_REQUEST)

    # Step 1: Create booking (simplified)
    booking = Booking.objects.create(user_email=user_email, details=booking_details, amount=amount)

    # Step 2: Initiate payment
    payload = {
        "amount": amount,
        "currency": "ETB",
        "email": user_email,
        "first_name": "Customer",
        "last_name": "Name",
        "tx_ref": f"BOOK-{booking.id}",
        "callback_url": f"https://yourdomain.com/payment/callback/"
    }

    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(CHAPA_API_URL, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and data.get("status") == "success":
            transaction_id = data['data']['tx_ref']

            # Step 3: Store payment record
            Payment.objects.create(
                booking_reference=f"BOOK-{booking.id}",
                transaction_id=transaction_id,
                amount=amount,
                status="PENDING"
            )

            return Response({
                "message": "Booking created and payment initiated",
                "checkout_url": data['data']['checkout_url'],
                "transaction_id": transaction_id
            }, status=status.HTTP_201_CREATED)
        else:
            booking.delete()  # rollback booking
            return Response({"error": "Failed to initiate payment", "details": data},
                            status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        booking.delete()  # rollback booking
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)