from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def wallet_page(request):
    wallet = request.user.wallet
    return render(request, "wallet/wallet.html", {
        "wallet": wallet,
        "transactions": wallet.transactions.all()[:30],
    })
