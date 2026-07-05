NAMESPACE ?= online-excel

.PHONY: k8s-build k8s-diff k8s-apply k8s-delete k8s-status k8s-logs

## Отрендерить манифесты (kustomize + helmCharts) без применения
k8s-build:
	kustomize build --enable-helm .

## Показать diff между текущим состоянием кластера и манифестами
k8s-diff:
	kustomize build --enable-helm . | kubectl diff -f - || true

## Развернуть/обновить весь стек одной командой
## server-side apply — иначе CRD Prometheus Operator не помещаются в
## аннотацию last-applied-configuration (лимит 262144 байт).
## Прогоняем дважды: первый проход создаёт CRD, второй — CR-объекты
## (Prometheus/ServiceMonitor/PrometheusRule), которые в первом проходе
## ещё не проходят, пока API-сервер не зарегистрирует новый CRD (Established).
k8s-apply:
	-kustomize build --enable-helm . | kubectl apply --server-side --force-conflicts -f -
	kustomize build --enable-helm . | kubectl apply --server-side --force-conflicts -f -

## Удалить всё, что описано в манифестах
k8s-delete:
	kustomize build --enable-helm . | kubectl delete -f - --ignore-not-found

## Статус подов/сервисов в namespace
k8s-status:
	kubectl get pods,svc,ingressroute -n $(NAMESPACE)

## Логи конкретного деплоймента: make k8s-logs SVC=table-service
k8s-logs:
	kubectl logs -n $(NAMESPACE) -f deployment/$(SVC)