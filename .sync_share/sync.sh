syncin() {

  pwd=$(pwd)

  read -r -p "Connect to git or GitHub? (y/n) " git

  if [[ $git == [yY] || $git == [yY][eE][sS] ]]; then

  cd $1 || return

  if [ ! -f ".gitignore" ]; then
    cp ~/.bash_backup/.gitignore .gitignore
  fi

    if [ -d $1 ]; then
      if [ -d ".git" ]; then
          echo -e "Setting Lukas2357/$1 as remote on branch main and pull content."
      else
          echo -e "Local folder $1 is not a git repo. Setting it up with Lukas2357/$1."
          git init &> /dev/null
      fi
      read -r -p  "Enter to commit/pull all files, make sure .gitignore is configured!"
      git checkout -b main
      git add .
      git commit -m 'Initial commit'
      git remote add origin git@github.com:Lukas2357/"$1".git
      git pull origin main --allow-unrelated-histories

    else
      cd .. || return

      git clone https://github.com/Lukas2357/"$1".git &> /dev/null
      if [ -d $1 ]; then
          echo -e "Success!"
      else
        git clone https://"$user"@github.com/Lukas2357/"$1" &> /dev/null
        if [ -d "$1" ]; then
            echo -e "Success!"
        else
            echo -e "-> Could not clone, are you sure you gave the correct user and have access to the repo?\n"
            echo "-> Continue without cloning in 10 sec, abort manually if you like to retry."
            sleep 10
            if [ ! -d $1 ]; then
                mkdir $1
            fi
          fi
        fi
      fi
  else
      if [ ! -d $1 ]; then
          mkdir $1
      fi
  fi

  cd $pwd || return
  cd $1 || return

  if [ -d ".sync" ]; then
      mv .sync/.last_modified.json .last_modified.json
      mv .sync/.gdriveignore .gdriveignore
      echo -e "Re-Cloning .sync from Lukas2357/GDriveSync..."
      rm -rf .sync
      git clone https://github.com/Lukas2357/GDriveSync.git .sync &> /dev/null
      mv -f .last_modified.json .sync/.last_modified.json
      mv -f .gdriveignore .sync/.gdriveignore
  else
      echo -e "Cloning .sync from Lukas2357/GDriveSync..."
      git clone https://github.com/Lukas2357/GDriveSync.git .sync &> /dev/null
  fi

  cd ".sync" || return
  if [ -d ".git" ]; then
      rm -rf ".git"
  fi

  python -c 'import sync; sync.extend_gitignore()'

  read -r -p "Main Google Account to connect: " account
  if [ -f ~/Tokens/"$account"/credentials.json ]; then
    cp -f ~/Tokens/"$account"/credentials.json credentials.json
  fi
  if [ -f ~/Tokens/"$account"/.gdriveignore ]; then
    cp -f ~/Tokens/"$account"/.gdriveignore .gdriveignore
  fi

  cd ..

  read -r -p "Connect Backup/Share account? (y/n) " ans
  if [ "$ans" != 'n' ]; then

    if [ -d .sync_share ]; then
      rm -rf .sync_share
    fi

    cp -r .sync .sync_share
    cd .sync_share || return

    if [ -f ~/Tokens/share/credentials.json ]; then
      cp -f ~/Tokens/share/credentials.json credentials.json
    fi
    if [ -f ~/Tokens/share/.gdriveignore ]; then
      cp -f ~/Tokens/share/.gdriveignore .gdriveignore
    fi

    cd .. || return

  fi

  read -p "-> Sync GDrive content now? (y/n) " ans

  if [[ $ans == [yY] || $ans == [yY][eE][sS] ]]; then
    prepare_git "Initial sync"
    if [ -d .sync ]; then
      echo -e "\nStarting to sync GDrive"
      cd .sync || return
      python3 sync.py -s $1
      cd ..
    fi
    sync_git "Initial sync"
  fi

  cd $pwd || return

  echo -e "-> You are good to go. Congrats!"

}


syncinit() {

  pwd=$(pwd)

  echo -e "\n### Combining GitHub and GDrive sync ###\n\n-> Let's get started...\n"
  echo -e "-> We first try to clone or connect a repo from GitHub"
  echo -e "-> If you have a local folder with the given name, we try to connect, else we clone."
  read -p "-> Do you have access to a repo with given name and like to connect/clone it? (y/n) " git

  if [[ $git == [yY] || $git == [yY][eE][sS] ]]; then

      read -p "-> Please give us the username of that repo: " user

      if [ -d $1 ]; then

          cd $1 || return

          if [ -d ".git" ]; then
              echo -e "\n-> Local folder $1 is a git repo."
              echo -e "\n-> Setting $user/$1 as remote on branch main and pull content..."
              git checkout -b main
              git remote add origin git@github.com:"$user"/"$1".git
              git pull origin main --allow-unrelated-histories
              echo -e "\n-> If it failed, you might abort and retry or add manually. We continue in any case..."
          else
              echo -e "\n-> Local folder $1 is not a git repo. Setting it up with $user/$1"
              git init
              git checkout -b main
              git remote add origin git@github.com:"$user"/"$1".git
              git pull origin main --allow-unrelated-histories
              echo -e "\n-> If it failed, you might abort and retry or add manually. We continue in any case..."
          fi

          cd $pwd || return

      else

          cd $1 || return
          cd .. || return

          echo -e "\n-> Trying to clone public repo...\n"
          git clone https://github.com/"$user"/"$1".git &> /dev/null

          if [ -d $1 ]; then
              echo -e "-> Success!\n"
          else
              echo -e "\n-> Trying to clone private repo...\n"
              git clone https://"$user"@github.com/"$user"/"$1" &> /dev/null

              if [ -d $1 ]; then
                  echo -e "-> Success!\n"
              else
                  echo -e "-> Could not clone, are you sure you gave the correct user and have access to the repo?\n"
                  echo "-> Continue without cloning in 10 sec, abort manually if you like to retry."
                  sleep 10
                  if [ ! -d $1 ]; then
                      mkdir $1
                  fi
              fi
          fi
      fi
  else
      if [ ! -d $1 ]; then
          mkdir $1
      fi
  fi

  cd $1 || return

  if [ -d ".sync" ]; then
      echo -e "-> Found .sync folder in $1, getting .last_modified.json and .gdriveignore...\n"
      mv .sync/.last_modified.json .last_modified.json
      mv .sync/.gdriveignore .gdriveignore
      echo -e "Re-Cloning .sync from Lukas2357/GDriveSync..."
      rm -rf .sync
      git clone https://github.com/Lukas2357/GDriveBackup.git .sync &> /dev/null
      echo -e "-> Plugging in previous .last_modified.json and .gdriveignore...\n"
      mv -f .last_modified.json .sync/.last_modified.json
      mv -f .gdriveignore .sync/.gdriveignore
  else
      echo -e "-> Cloning .sync from Lukas2357/GDriveBackup...\n"
      git clone https://github.com/Lukas2357/GDriveBackup.git .sync &> /dev/null
  fi

  cd ".sync" || return
  if [ -d ".git" ]; then
      rm -rf ".git"
  fi

  python -c 'import sync; sync.extend_gitignore()'

  read -r -p "Main Google Account to connect: " account
  if [ -f ~/Tokens/"$account"/credentials.json ]; then
    cp -f ~/Tokens/"$account"/credentials.json credentials.json
  fi

  cd ..

  read -r -p "Backup/Share Google Account to connect (n for none): " account
  if [ "$account" != 'n' ]; then

    if [ -d .sync_"$account" ]; then
      rm -rf .sync_"$account"
    fi

    cp -r .sync .sync_"$account"
    cd .sync_"$account" || return

    if [ -d ".git" ]; then
      rm -rf ".git"
    fi

    if [ -f ~/Tokens/"$account"/credentials.json ]; then
      cp -f ~/Tokens/"$account"/credentials.json credentials.json
    else
      rm credentials.json
    fi

    cd .. || return

  fi

  if [[ $git == [yY] || $git == [yY][eE][sS] ]]; then
    echo -e "\n-> You can now add, commit and pull all files or do this manually in another terminal."
    read -r -p "-> Do you want to add, commit and push all files? (y/n): " ans

    if [[ $ans == [yY] || $ans == [yY][eE][sS] ]]; then
      git add .
      git commit -m 'initial sync commit'
      git pull origin main --allow-unrelated-histories
    fi
  fi

  echo -e "\n-> Sync requires pydrive. If you continue it is installed via pip (if not already installed)."
  echo -e "-> If you prefer manual install or using virtual environment, quit and prepare it, then rerun.\n"
  read -r -p "-> Continue? (y/n): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || return;
  pip install pydrive &> /dev/null
  echo -e "-> Installed pydrive using pip (if not already)\n\n"

  echo "-> Everything prepared. You can now call..."
  echo -e "-> 'bash .sync/sync.sh sync' to sync GDrive bidirectional (local->GDrive, GDrive->local)"
  echo -e "-> 'bash .sync/sync.sh sync_down' to just download from GDrive"
  echo -e "-> 'bash .sync/sync.sh sync_up' to just upload to GDrive"
  echo -e "-> 'bash .sync/sync.sh sync_clean' to delete GDrive and replace with local (only if messed up!)\n"
  echo -e "-> 'bash .sync/sync.sh sync_copy' to sync with GitHub + create copy (with date) of local in GDrive"

  echo -e "-> If you have git/GitHub connected, all added files will be committed/pushed in any case."
  echo -e "-> For convenience put content of .sync/sync.sh in .bash_functions and call 'sync' etc. directly."

  echo -e "-> Full sync with the cloud will always keep the newer file versions.\n"
  echo -e "-> It is recommended to sync GDrive content now, to be up to date.\n"
  read -p "-> Sync GDrive content now? (y/n) " ans

  if [[ $ans == [yY] || $ans == [yY][eE][sS] ]]; then
    prepare_git "Initial sync"
    if [ -d .sync ]; then
      echo -e "\nStarting to sync GDrive"
      cd .sync || return
      python3 sync.py -s $1
      cd ..
    fi
    sync_git "Initial sync"
  fi

  cd $pwd || return

  echo -e "\n-> You are good to go. Congrats!\n"

}

prepare_git() {
  if [ -d ".git" ]; then
    echo "Pulling content from git/GitHub"
    if [ "$1" == "initial sync" ]; then
      git branch --set-upstream-to=origin/main main
    fi
    git pull origin main
  fi
}

sync_git() {
  if [ -d ".git" ]; then
    git add .
    echo "Committing content to local git repo"
    git commit -m "$1"
    echo "Pushing content to remote GitHub repo"
    if [ "$1" == "initial sync" ]; then
      git push --set-upstream origin main &> /dev/null
    else
      git push origin main
    fi
  fi
  echo -e "\nEverything up to date :)"
}

sync() {
  prepare_git "$2"
  if [ -d .sync ]; then
    echo -e "\nStarting to sync GDrive"
    cd .sync || return
    if [ "$1" == "down" ]; then
      python3 sync.py -s .. -dl True
    elif [ "$1" == "up" ]; then
      python3 sync.py -s .. -ul True
    elif [ "$1" == "clean" ]; then
      python3 sync.py -s .. -c True
    elif [ "$1" == "bid" ]; then
      python3 sync.py -s ..
    fi
    cd ..
  fi
  for folder in .sync_*; do
    if [[ "$1" == "full" || "$1" == "back" ]]; then
      echo -e "\nStarting backup sync"
      cd "$folder" || return
      python3 sync.py -s .. -ul True -cp True
      cd ..
    fi
  done
  sync_git "$2"
}

"$@"
