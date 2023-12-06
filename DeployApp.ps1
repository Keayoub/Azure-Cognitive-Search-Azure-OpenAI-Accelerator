.\infra\scripts\CreatePrerequisites.ps1

cd ./infra/target/backend
Remove-Item * -Recurse;Copy-Item -Path "../../../apps/backend/*" -Destination "./" -force;Copy-Item -Path "../../../common/*" -Destination "./" -Recurse -force;pip install -r requirements.txt
cd..
zip -j backend.zip ./backend/*
cd frontend
Remove-Item * -Recurse; Copy-Item -Path "../../../apps/frontend/*" -Destination "./" -Recurse -Force; Copy-Item -Path "../../../apps/frontend/pages/*" -Destination "./pages"; Copy-Item -Path "../../../common/*" -Destination "./" -Recurse -force;pip install -r requirements.txt
cd ../frontend
zip -r ../frontend.zip ./*
# Return to target folder
cd ..
#az webapp deployment source config-zip --resource-group "rg-oaixoalab04-uq5k6hqnso4yc" --name "webApp-Backend-BotId-sjfiuqfabeg52" --src "backend.zip"
#az webapp deployment source config-zip --resource-group "rg-oaixoalab04-uq5k6hqnso4yc" --name "webApp-Frontend-sjfiuqfabeg52" --src "frontend.zip"
# Return to root folder
cd ../..