"""Human-readable measured characteristics, selection and verification status."""
import json


def build_review(report):
    analysis=report['source_analysis']
    discovery=analysis['components'][0]['feature_discovery']
    rows=[]
    for c in discovery['dimension_candidates']:
        r=report['dimensions'][c['id']]
        value=r.get('source_feature',{}).get('independent_source_value_mm',c['value'])
        rows.append({'stable_id':c['stable_id'],'candidate_id':c['id'],'label':c['label'],'kind':c['kind'],
                     'measured_value':value,'units':c['units'],'selected':r['selected'], 'drawing_status':r['status'],
                     'source_verification':c['verification_status'],
                     'native_verification':r.get('verification'), 'reason':r.get('reason',r['selection_reason']),
                     'view_role':r.get('view_role')})
    component=analysis['components'][0]
    return {'preliminary':True,'engineering_verification_required':True,'source':report['source'],
            'source_validation':analysis['validation'], 'characteristics':rows,
            'features':discovery['features'], 'semantic_recognition':component['recognition'],
            'unmapped_faces':discovery['unmapped_faces'], 'recognition_limitations':discovery.get('limitations',[]),
            'section_diagnostics':report.get('section_diagnostics',{}),
            'notice':discovery['coverage_notice']}


def write_review(path, review):
    path.write_text(json.dumps(review,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# Engineering review', '',review['source'], '', 'PRELIMINARY - engineering verification required.', '',review['notice'],'',
           '| Source characteristic | Measured value | Selected | Drawing / verification status | Stable identity |',
           '| --- | --- | --- | --- | --- |']
    for r in review['characteristics']:
        measured='unresolved' if r['measured_value'] is None else f"{r['measured_value']:.8g} {r['units']}"
        lines.append(f"| {r['label']} | {measured} | {'yes' if r['selected'] else 'no'} | {r['drawing_status']} / {r['source_verification']} | `{r['stable_id']}` |")
    lines += ['', '## Selection and unresolved evidence', '']
    for r in review['characteristics']:
        lines.append(f"- {r['candidate_id']} {r['label']}: {r['reason']}")
    lines += ['', '## Source validation', '', '```json',json.dumps(review['source_validation'],indent=2),'```','',
              '## Semantic recognition (measured roles are inferences)', '', '```json',json.dumps(review['semantic_recognition'],indent=2),'```','',
              '## Unclassified source faces', '',json.dumps(review['unmapped_faces'],indent=2),'',
              'Configuration controls selection, never measurement overrides. Missing support stays unresolved. No manufacturing tolerances, thread designations, material, finish or GD&T are assigned.']
    path.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
