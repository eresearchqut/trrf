from django.db.models import F, Count


def working_group_optgroup_choices(wg_queryset, make_option_fn=None):
    def default_make_option_fn(working_group):
        # e.g. <option value="{{working_group.id}}">{{working_group}}</option>
        return working_group.id, working_group

    make_option_fn = make_option_fn or default_make_option_fn
    wg_types = wg_queryset.values('type').annotate(name=F('type__name'), type_cnt=Count('type')).order_by()
    return [(wg_type.get('name'), [make_option_fn(wg)
                                   for wg in wg_queryset.filter(type=wg_type.get('type'))])
            for wg_type in wg_types]