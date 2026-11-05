from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat, TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegistrationForm, VisitFilterForm
from .models import Office, Visit, Visitor


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'visitors/login.html')


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    period = 'month' if request.GET.get('period') == 'month' else 'week'
    days = 30 if period == 'month' else 7
    start = today - timedelta(days=days - 1)
    daily = dict(Visit.objects.filter(time_in__date__gte=start, time_in__date__lte=today)
                 .annotate(day=TruncDate('time_in')).values('day').annotate(total=Count('pk')).values_list('day', 'total'))
    trend = [{'date': start + timedelta(days=i), 'total': daily.get(start + timedelta(days=i), 0)} for i in range(days)]
    type_summary = list(Visit.objects.values('visitor__visitor_type').annotate(total=Count('pk')).order_by('-total', 'visitor__visitor_type'))
    total_visits = sum(item['total'] for item in type_summary)
    palette = dict(zip((value for value, label in Visitor.VISITOR_TYPES),
                       ('#6D1926', '#286044', '#A65066', '#52866A', '#50101B', '#153C2C', '#84B599')))
    segments = []
    position = 0
    for item in type_summary:
        item['color'] = palette.get(item['visitor__visitor_type'], '#84B599')
        end = position + item['total'] / total_visits * 100
        segments.append(f"{item['color']} {position:.4f}% {end:.4f}%")
        position = end
    office_summary = list(Visit.objects.values('office__office_name').annotate(total=Count('pk')).order_by('-total', 'office__office_name')[:5])
    return render(request, 'visitors/dashboard.html', {
        'visitors_today': Visit.objects.filter(time_in__date=today).count(),
        'currently_inside': Visit.objects.filter(status='Inside').count(),
        'completed_today': Visit.objects.filter(status='Completed', time_out__date=today).count(),
        'visitors_this_month': Visit.objects.filter(time_in__year=today.year, time_in__month=today.month).count(),
        'recent_visits': Visit.objects.select_related('visitor', 'office', 'recorded_by').order_by('-time_in', '-pk')[:8],
        'type_summary': type_summary,
        'type_gradient': ', '.join(segments) if segments else '#DAE5DE 0% 100%',
        'office_summary': office_summary,
        'office_max': max((item['total'] for item in office_summary), default=1),
        'trend': trend,
        'trend_max': max((item['total'] for item in trend), default=0) or 1,
        'trend_total': sum(item['total'] for item in trend),
        'period': period,
        'trend_days': days,
        'total_visits': total_visits,
    })


@login_required
def register_visitor_view(request):
    selected = None
    if request.method == 'GET' and request.GET.get('visitor', '').isdigit():
        selected = get_object_or_404(Visitor, pk=request.GET['visitor'])
    initial = {field: getattr(selected, field) for field in
               ('first_name', 'last_name', 'contact_number', 'address', 'visitor_type', 'visitor_type_other')} if selected else {}
    initial['visitor'] = selected
    form = RegistrationForm(request.POST if request.method == 'POST' else None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            visitor = data['visitor']
            if visitor is None:
                matches = list(Visitor.objects.filter(first_name__iexact=data['first_name'],
                               last_name__iexact=data['last_name'], contact_number=data['contact_number'])[:2])
                if len(matches) > 1:
                    form.add_error(None, 'Several matching profiles exist. Locate and select the returning visitor first.')
                elif matches:
                    visitor = matches[0]
            if not form.errors:
                if visitor:
                    visitor = Visitor.objects.select_for_update().get(pk=visitor.pk)
                if visitor and visitor.visits.filter(status='Inside').exists():
                    form.add_error(None, 'This visitor is already inside. Record their time-out before starting another visit.')
                else:
                    visitor = visitor or Visitor()
                    for field in ('first_name', 'last_name', 'contact_number', 'address', 'visitor_type', 'visitor_type_other'):
                        setattr(visitor, field, data[field])
                    visitor.save()
                    Visit.objects.create(visitor=visitor, office=data['office'], recorded_by=request.user,
                                         purpose=data['purpose'], person_to_visit=data['person_to_visit'])
                    messages.success(request, f'Time-in recorded for {visitor.first_name} {visitor.last_name}.')
                    return redirect('active_visitors')
    query = request.GET.get('q', '').strip()[:200]
    matches = Visitor.objects.none()
    if query:
        matches = Visitor.objects.annotate(full_name=Concat('first_name', Value(' '), 'last_name')).filter(
            Q(full_name__icontains=query) | Q(contact_number__icontains=query)).order_by('last_name', 'first_name')[:20]
    return render(request, 'visitors/register_visitor.html', {
        'form': form, 'matches': matches, 'query': query, 'selected': selected,
        'has_offices': Office.objects.exists(),
    })


@login_required
def active_visitors_view(request):
    if request.method == 'POST':
        raw_id = request.POST.get('visit_id', '')
        if not raw_id.isdigit():
            messages.error(request, 'Select a valid visit to record time-out.')
            return redirect('active_visitors')
        visit = get_object_or_404(Visit.objects.select_related('visitor'), pk=raw_id)
        updated = Visit.objects.filter(pk=visit.pk, status='Inside', time_out__isnull=True).update(
            time_out=timezone.now(), status='Completed')
        if updated:
            messages.success(request, f'Time-out recorded for {visit.visitor.first_name} {visit.visitor.last_name}.')
        else:
            messages.info(request, 'This visit was already completed. Its original time-out has been kept.')
        return redirect('active_visitors')
    form = VisitFilterForm(request.GET)
    visits = form.filter(Visit.objects.filter(status='Inside').select_related('visitor', 'office', 'recorded_by'))
    page = Paginator(visits.order_by('-time_in', '-pk'), 25).get_page(request.GET.get('page'))
    return render(request, 'visitors/active_visitors.html', {'active_visits': page, 'page_obj': page, 'form': form})


@login_required
def visitor_history_view(request):
    form = VisitFilterForm(request.GET)
    visits = form.filter(Visit.objects.select_related('visitor', 'office', 'recorded_by'))
    page = Paginator(visits.order_by('-time_in', '-pk'), 25).get_page(request.GET.get('page'))
    return render(request, 'visitors/visitor_history.html', {'visits': page, 'page_obj': page, 'form': form})


@login_required
def reports_view(request):
    form = VisitFilterForm(request.GET)
    visits = form.filter(Visit.objects.select_related('visitor', 'office'))
    return render(request, 'visitors/reports.html', {
        'form': form,
        'total_visits': visits.count(),
        'inside': visits.filter(status='Inside').count(),
        'completed': visits.filter(status='Completed').count(),
        'by_type': visits.values('visitor__visitor_type').annotate(total=Count('pk')).order_by('-total'),
        'by_office': visits.values('office__office_name').annotate(total=Count('pk')).order_by('-total'),
    })


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')
