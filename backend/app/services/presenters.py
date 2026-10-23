"""Сборка ответов API о заявке: тексты из labels.yaml, кнопки, таймлайн.

Здесь «переводится» внутреннее состояние заявки в то, что видит человек.
Фронт ничего не вычисляет — он показывает поля этих ответов.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.business_config import get_business_config
from app.domain.payments import payment_summary
from app.domain.progress import EventInfo, build_progress
from app.domain.state_machine import available_actions, get_current_offer, get_open_info_request
from app.domain.statuses import FINAL_STATUSES, Actor, ApplicationStatus
from app.models import Application, ApplicationEvent, Company, Document, InfoRequest, Offer
from app.schemas.application import (
    ActionOut,
    ApplicationOut,
    InfoRequestOut,
    OfferOut,
    ProductShort,
    ProgressStep,
    RequestedDocument,
    RequestedField,
    TimelineItem,
)
from app.schemas.company import CompanyOut, DocumentOut


def build_actions(db: Session, application: Application, viewer: Actor) -> list[ActionOut]:
    labels = get_business_config().labels
    result = []
    for item in available_actions(db, application, viewer):
        action_label = labels.actions.get(item.code)
        result.append(
            ActionOut(
                code=item.code,
                label=action_label.label if action_label else item.code,
                enabled=item.enabled,
                disabled_reason=item.disabled_reason,
                requires_comment=item.requires_comment,
                confirm_text=action_label.confirm_text if action_label else None,
            )
        )
    return result


def actor_label(actor_type: str, viewer: Actor) -> str:
    actors = get_business_config().labels.actors
    if actor_type == Actor.CLIENT and viewer == Actor.CLIENT:
        return actors["client_self"]
    return actors.get(actor_type, actor_type)


def load_events(db: Session, application: Application) -> list[ApplicationEvent]:
    return list(
        db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == application.id).order_by(ApplicationEvent.created_at))
    )


def build_progress_steps(application: Application, events: list[ApplicationEvent]) -> list[ProgressStep]:
    labels = get_business_config().labels
    event_infos = [EventInfo(action=event.action, from_status=event.from_status, to_status=event.to_status) for event in events]
    return [
        ProgressStep(code=code, label=labels.progress_steps[code], state=state, state_label=labels.progress_states[state])
        for code, state in build_progress(application.status, event_infos)
    ]


def build_timeline(db: Session, application: Application, viewer: Actor, events: list[ApplicationEvent] | None = None) -> list[TimelineItem]:
    labels = get_business_config().labels
    events = load_events(db, application) if events is None else events
    return [
        TimelineItem(
            at=event.created_at,
            action=event.action,
            title=labels.timeline.get(event.action, labels.statuses[event.to_status].label),
            status=event.to_status,
            status_label=labels.statuses[event.to_status].label,
            actor=actor_label(event.actor_type, viewer),
            comment=event.comment,
        )
        for event in events
    ]


def build_offer(offer: Offer) -> OfferOut:
    labels = get_business_config().labels
    summary = payment_summary(offer.amount, offer.rate, offer.term_months)
    return OfferOut(
        id=offer.id,
        offer_type=offer.offer_type,
        offer_type_label=labels.offer_types.get(offer.offer_type, offer.offer_type),
        amount=offer.amount,
        term_months=offer.term_months,
        rate=offer.rate,
        monthly_payment=offer.monthly_payment,
        total_payment=summary["total_payment"],
        overpayment=summary["overpayment"],
        valid_until=offer.valid_until,
        status=offer.status,
        status_label=labels.offer_statuses.get(offer.status, offer.status),
        created_at=offer.created_at,
    )


def build_info_request(db: Session, info_request: InfoRequest, viewer: Actor) -> InfoRequestOut:
    config = get_business_config()
    uploaded_kinds = set(
        db.scalars(
            select(Document.kind).where(
                Document.application_id == info_request.application_id,
                Document.created_at >= info_request.created_at,
            )
        )
    )
    documents = []
    for kind in info_request.requested_documents:
        kind_config = config.dictionaries.document_kind(kind)
        documents.append(RequestedDocument(kind=kind, label=kind_config.label if kind_config else kind, uploaded=kind in uploaded_kinds))
    fields = [
        RequestedField(field=item["field"], label=config.labels.fields.get(item["field"], item["field"]), message=item.get("message"))
        for item in info_request.requested_fields
    ]
    return InfoRequestOut(
        id=info_request.id,
        comment=info_request.comment,
        fields=fields,
        documents=documents,
        created_by=actor_label(info_request.created_by_type, viewer),
        created_at=info_request.created_at,
        is_open=info_request.is_open,
        response_comment=info_request.response_comment,
    )


def status_texts(application: Application, viewer: Actor) -> tuple[str, str]:
    status = get_business_config().labels.statuses[application.status]
    description = status.employee_description if viewer == Actor.EMPLOYEE else status.description
    return status.label, description


def build_application_out(db: Session, application: Application, viewer: Actor) -> ApplicationOut:
    config = get_business_config()
    status_label, status_description = status_texts(application, viewer)
    purpose = config.dictionaries.purpose(application.purpose_code)

    info_request = None
    if application.status == ApplicationStatus.NEEDS_INFO:
        open_request = get_open_info_request(db, application.id)
        if open_request:
            info_request = build_info_request(db, open_request, viewer)

    offer = get_current_offer(db, application.id)
    events = load_events(db, application)
    documents_count = db.scalar(select(func.count()).select_from(Document).where(Document.application_id == application.id))

    return ApplicationOut(
        id=application.id,
        number=application.number,
        status=application.status,
        status_label=status_label,
        status_description=status_description,
        is_final=application.status in FINAL_STATUSES,
        product=ProductShort(code=application.product.code, name=application.product.name),
        amount=application.amount,
        term_months=application.term_months,
        purpose_code=application.purpose_code,
        purpose_label=purpose.label if purpose else None,
        purpose_comment=application.purpose_comment,
        collateral_description=application.collateral_description,
        monthly_revenue=application.monthly_revenue,
        monthly_expenses=application.monthly_expenses,
        current_loan_payments=application.current_loan_payments,
        version=application.version,
        created_at=application.created_at,
        updated_at=application.updated_at,
        submitted_at=application.submitted_at,
        available_actions=build_actions(db, application, viewer),
        progress=build_progress_steps(application, events),
        timeline=build_timeline(db, application, viewer, events),
        info_request=info_request,
        offer=build_offer(offer) if offer else None,
        documents_count=documents_count or 0,
    )


def build_company(company: Company) -> CompanyOut:
    company_types = get_business_config().dictionaries.company_types
    return CompanyOut(
        id=company.id,
        inn=company.inn,
        ogrn=company.ogrn,
        company_type=company.company_type,
        company_type_label=company_types.get(company.company_type, company.company_type),
        name=company.name,
        okved=company.okved,
        industry=company.industry,
        registration_date=company.registration_date,
        region=company.region,
        annual_revenue=company.annual_revenue,
        employees_count=company.employees_count,
    )


def build_document(document: Document, viewer: Actor) -> DocumentOut:
    config = get_business_config()
    kind = config.dictionaries.document_kind(document.kind)
    if viewer == Actor.EMPLOYEE:
        base = f"/api/v1/backoffice/applications/{document.application_id}"
    else:
        base = f"/api/v1/applications/{document.application_id}"
    uploaded_by = actor_label(Actor.SYSTEM.value if document.uploaded_by_user_id is None else Actor.CLIENT.value, viewer)
    return DocumentOut(
        id=document.id,
        kind=document.kind,
        kind_label=kind.label if kind else document.kind,
        filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        uploaded_by=uploaded_by,
        created_at=document.created_at,
        download_url=f"{base}/documents/{document.id}/download",
    )
